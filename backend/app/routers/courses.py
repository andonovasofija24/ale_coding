"""
Courses: members and groups.

Routes
  /courses                       my courses; create (professors)
  /courses/join                  join with a code (students)
  /courses/{id}                  details (+ assignments I can see); edit; new join code
  /courses/{id}/groups           groups
  /courses/{id}/members          staff: list, add by e-mail, change role/group, remove

Assignments, submissions, exams, grading and the gradebook live in routers/assignments.py.
"""
import secrets
import uuid
from datetime import datetime, timezone
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import access
from app.core.deps import get_current_user
from app.core.security import avatar_url
from app.database import get_db
from app.models.course import Assignment, Course, CourseGroup, CourseMember
from app.models.user import User
from app.routers import assignments
from app.services import content, observability

router = APIRouter(tags=["courses"], dependencies=[Depends(content.use_language)])

_CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # no 0/O, 1/I


def _new_join_code() -> str:
    return "".join(secrets.choice(_CODE_ALPHABET) for _ in range(7))


def _utc_naive(dt: Optional[datetime]) -> Optional[datetime]:
    """Store times as naive UTC (the rest of the database does the same)."""
    if dt is None:
        return None
    return dt.astimezone(timezone.utc).replace(tzinfo=None) if dt.tzinfo else dt


def _iso(dt: Optional[datetime]) -> Optional[str]:
    return dt.replace(tzinfo=timezone.utc).isoformat() if dt else None


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class CourseIn(BaseModel):
    code: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=300)
    semester: str = Field("", max_length=100)
    description: str = ""
    subject_id: Optional[uuid.UUID] = None


class CourseUpdate(BaseModel):
    code: Optional[str] = Field(None, min_length=1, max_length=50)
    name: Optional[str] = Field(None, min_length=1, max_length=300)
    semester: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    join_enabled: Optional[bool] = None
    archived: Optional[bool] = None
    language: Optional[Literal["mk", "en"]] = None
    reminders_enabled: Optional[bool] = None
    reminder_hours: Optional[int] = Field(None, ge=1, le=168)
    subject_id: Optional[uuid.UUID] = None
    clear_subject: bool = False


class JoinIn(BaseModel):
    code: str


class GroupIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    language: Optional[Literal["mk", "en"]] = None  # teaching language of the group (None = the course's)


class MembersIn(BaseModel):
    emails: list[str] = Field(min_length=1, max_length=1000)
    role: Literal["student", "lab", "assistant", "teacher"] = "student"
    group_id: Optional[uuid.UUID] = None


class MemberUpdate(BaseModel):
    role: Optional[Literal["student", "lab", "assistant", "teacher"]] = None
    group_id: Optional[uuid.UUID] = None
    clear_group: bool = False
    unlock_role: bool = False   # let Moodle (LTI) set this person's role again


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _course_out(c: Course, role: str, students: int = 0) -> dict:
    staff = role in access.COURSE_STAFF
    return {
        "id": str(c.id), "code": c.code, "name": c.name, "semester": c.semester, "description": c.description,
        "archived": c.archived, "my_role": role, "students": students,
        "join_code": c.join_code if staff else None, "join_enabled": c.join_enabled if staff else None,
        "language": c.language, "reminders_enabled": c.reminders_enabled, "reminder_hours": c.reminder_hours,
        "subject_id": str(c.subject_id) if c.subject_id else None,
    }


async def _student_counts(db: AsyncSession, course_ids: list) -> dict:
    if not course_ids:
        return {}
    rows = (await db.execute(
        select(CourseMember.course_id, func.count()).where(
            CourseMember.course_id.in_(course_ids), CourseMember.role == "student"
        ).group_by(CourseMember.course_id)
    )).all()
    return {str(cid): n for cid, n in rows}


async def _check_subject(db: AsyncSession, subject_id) -> None:
    from app.models.task import Subject
    if subject_id and not (await db.execute(select(Subject.id).where(Subject.id == subject_id))).first():
        raise HTTPException(status_code=422, detail="Subject not found")


async def _groups_map(db: AsyncSession, course_id) -> dict:
    rows = (await db.execute(select(CourseGroup).where(CourseGroup.course_id == course_id))).scalars().all()
    return {str(g.id): g.name for g in rows}


# ---------------------------------------------------------------------------
# Courses
# ---------------------------------------------------------------------------

@router.get("/courses")
async def my_courses(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    if user.role == "admin":
        rows = [(c, "teacher") for c in (await db.execute(select(Course).order_by(Course.created_at.desc()))).scalars()]
    else:
        rows = (await db.execute(
            select(Course, CourseMember.role).join(CourseMember, CourseMember.course_id == Course.id)
            .where(CourseMember.user_id == user.id).order_by(Course.created_at.desc())
        )).all()
    counts = await _student_counts(db, [c.id for c, _ in rows])
    out = [_course_out(c, role, counts.get(str(c.id), 0)) for c, role in rows]

    # For students: the next deadline in each course
    now = datetime.utcnow()
    if out:
        nxt = (await db.execute(
            select(Assignment.course_id, func.min(Assignment.due_at)).where(
                Assignment.course_id.in_([c.id for c, _ in rows]), Assignment.due_at > now,
                access.visible_to_student_clause(user, now)
            ).group_by(Assignment.course_id)
        )).all()
        nd = {str(cid): _iso(d) for cid, d in nxt}
        for c in out:
            c["next_due"] = nd.get(c["id"])
    return out


@router.post("/courses", status_code=201)
async def create_course(body: CourseIn, db: AsyncSession = Depends(get_db), user: User = Depends(access.get_course_creator)):
    await _check_subject(db, body.subject_id)
    course = Course(code=body.code.strip(), name=body.name.strip(), semester=body.semester.strip(),
                    description=body.description, join_code=_new_join_code(), created_by=user.id, subject_id=body.subject_id)
    db.add(course)
    await db.commit()  # the admin then puts the professor, assistants, лаборанти and students in it
    observability.set_context(course_id=course.id)
    await observability.activity("course_create", code=course.code, name=course.name)
    return _course_out(course, "teacher")


@router.delete("/courses/{course_id}", status_code=204)
async def delete_course(course_id: uuid.UUID, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    """Admin: delete a course with everything in it (assignments, submissions, grades, mail, materials)."""
    access.require_admin(user)
    course = (await db.execute(select(Course).where(Course.id == course_id))).scalar_one_or_none()
    if course is None:
        raise HTTPException(status_code=404, detail="Course not found")
    code, name = course.code, course.name
    await db.delete(course)
    await db.commit()
    await observability.activity("course_delete", code=code, name=name)


@router.get("/admin/courses")
async def admin_courses(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    """Admin: every course with its subject and its people by role."""
    access.require_admin(user)
    courses = (await db.execute(select(Course).order_by(Course.archived, Course.created_at.desc()))).scalars().all()
    people = (await db.execute(select(CourseMember.course_id, CourseMember.role, User.name)
                               .join(User, User.id == CourseMember.user_id))).all()
    by: dict = {}
    for cid, role, name in people:
        by.setdefault(str(cid), {}).setdefault(role, []).append(name)
    out = []
    for c in courses:
        p = by.get(str(c.id), {})
        out.append({**_course_out(c, "teacher", len(p.get("student", []))),
                    "teachers": sorted(p.get("teacher", [])), "assistants": sorted(p.get("assistant", [])),
                    "labs": sorted(p.get("lab", []))})
    return out


@router.post("/courses/join")
async def join_course(body: JoinIn, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    """Kept only for old clients: people are put in courses by the administrator."""
    raise HTTPException(status_code=403, detail="Only the administrator manages courses and people")
    code = body.code.strip().upper()
    course = (await db.execute(select(Course).where(Course.join_code == code))).scalar_one_or_none()
    if course is None or not course.join_enabled or course.archived:
        raise HTTPException(status_code=404, detail="Invalid course code")
    m = await access.membership(db, user, course.id)
    if m is None:
        m = CourseMember(course_id=course.id, user_id=user.id, role="student")
        db.add(m)
        await db.commit()
    return _course_out(course, m.role)


@router.get("/courses/{course_id}")
async def course_detail(course_id: uuid.UUID, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    course, role = await access.load_course(db, user, course_id)
    groups = await _groups_map(db, course.id)

    out_assignments = await assignments.assignments_for_course(db, course, user, role in access.COURSE_GRADERS,
                                                               lab_only=role == "lab")

    my_group = None
    if role == "student":
        m = await access.membership(db, user, course.id)
        my_group = groups.get(str(m.group_id)) if m and m.group_id else None
    counts = await _student_counts(db, [course.id])
    return {
        **_course_out(course, role, counts.get(str(course.id), 0)),
        "groups": [{"id": str(g.id), "name": g.name, "language": g.language} for g in sorted(
            (await db.execute(select(CourseGroup).where(CourseGroup.course_id == course.id))).scalars(), key=lambda g: g.name)],
        "my_group": my_group,
        "assignments": out_assignments,
    }


@router.patch("/courses/{course_id}")
async def update_course(course_id: uuid.UUID, body: CourseUpdate, db: AsyncSession = Depends(get_db),
                        user: User = Depends(get_current_user)):
    access.require_admin(user)
    course, role = await access.load_course(db, user, course_id, ("teacher",))
    await _check_subject(db, body.subject_id)
    if body.clear_subject:
        course.subject_id = None
    for k, v in body.model_dump(exclude_none=True, exclude={"clear_subject"}).items():
        setattr(course, k, v.strip() if isinstance(v, str) and k != "description" else v)
    await db.commit()
    return _course_out(course, role)


@router.post("/courses/{course_id}/join-code")
async def regenerate_join_code(course_id: uuid.UUID, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    access.require_admin(user)
    course, role = await access.load_course(db, user, course_id, ("teacher",))
    course.join_code = _new_join_code()
    await db.commit()
    return _course_out(course, role)


# ---------------------------------------------------------------------------
# Groups
# ---------------------------------------------------------------------------

@router.post("/courses/{course_id}/groups", status_code=201)
async def create_group(course_id: uuid.UUID, body: GroupIn, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    access.require_admin(user)
    await access.load_course(db, user, course_id, access.COURSE_STAFF)
    g = CourseGroup(course_id=course_id, name=body.name.strip(), language=body.language)
    db.add(g)
    await db.commit()
    return {"id": str(g.id), "name": g.name, "language": g.language}


@router.patch("/courses/{course_id}/groups/{group_id}")
async def rename_group(course_id: uuid.UUID, group_id: uuid.UUID, body: GroupIn, db: AsyncSession = Depends(get_db),
                       user: User = Depends(get_current_user)):
    access.require_admin(user)
    await access.load_course(db, user, course_id, access.COURSE_STAFF)
    g = (await db.execute(select(CourseGroup).where(CourseGroup.id == group_id, CourseGroup.course_id == course_id))).scalar_one_or_none()
    if g is None:
        raise HTTPException(status_code=404, detail="Group not found")
    g.name = body.name.strip()
    if "language" in body.model_fields_set:
        g.language = body.language
    await db.commit()
    return {"id": str(g.id), "name": g.name, "language": g.language}


@router.delete("/courses/{course_id}/groups/{group_id}", status_code=204)
async def delete_group(course_id: uuid.UUID, group_id: uuid.UUID, db: AsyncSession = Depends(get_db),
                       user: User = Depends(get_current_user)):
    access.require_admin(user)
    await access.load_course(db, user, course_id, access.COURSE_STAFF)
    await db.execute(delete(CourseGroup).where(CourseGroup.id == group_id, CourseGroup.course_id == course_id))
    await db.commit()


# ---------------------------------------------------------------------------
# Members
# ---------------------------------------------------------------------------

@router.get("/courses/{course_id}/members")
async def list_members(course_id: uuid.UUID, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    await access.load_course(db, user, course_id, access.COURSE_STAFF)
    groups = await _groups_map(db, course_id)
    rows = (await db.execute(
        select(CourseMember, User).join(User, User.id == CourseMember.user_id)
        .where(CourseMember.course_id == course_id).order_by(CourseMember.role.desc(), User.name)
    )).all()
    return [{"user_id": str(u.id), "name": u.name, "email": u.email, "role": m.role,
             "avatar_url": avatar_url(u.id, u.avatar_version),
             "group_id": str(m.group_id) if m.group_id else None,
             "group_name": groups.get(str(m.group_id)) if m.group_id else None,
             "role_locked": m.role_locked, "joined_at": _iso(m.joined_at)} for m, u in rows]


@router.post("/courses/{course_id}/members")
async def add_members(course_id: uuid.UUID, body: MembersIn, db: AsyncSession = Depends(get_db),
                      user: User = Depends(get_current_user)):
    """Add existing accounts by e-mail (one per line / comma separated in the UI). Unknown e-mails are returned,
    so those students can join with the course code once they have an account."""
    access.require_admin(user)
    _, role = await access.load_course(db, user, course_id, access.COURSE_STAFF)

    if body.group_id and not (await db.execute(select(CourseGroup.id).where(
            CourseGroup.id == body.group_id, CourseGroup.course_id == course_id))).first():
        raise HTTPException(status_code=422, detail="Group not found")
    emails = list(dict.fromkeys(e.strip().lower() for e in body.emails if e.strip()))
    users = {u.email.lower(): u for u in (await db.execute(
        select(User).where(func.lower(User.email).in_(emails)))).scalars()}
    added, already, not_found = [], [], []
    for e in emails:
        u = users.get(e)
        if u is None:
            not_found.append(e)
            continue
        m = await access.membership(db, u, course_id)
        if m:
            already.append(e)
            if body.group_id:
                m.group_id = body.group_id
            if m.role != body.role and m.role != "teacher":   # e.g. someone Moodle brought in gets their real role
                m.role = body.role
            m.role_locked = True
            continue
        # a role the admin gives is locked: Moodle (LTI) doesn't change it
        db.add(CourseMember(course_id=course_id, user_id=u.id, role=body.role, group_id=body.group_id, role_locked=True))
        added.append(e)
    await db.commit()
    await observability.activity("members_add", role=body.role, added=len(added), already=len(already) or None,
                                 not_found=len(not_found) or None)
    return {"added": added, "already": already, "not_found": not_found}


@router.patch("/courses/{course_id}/members/{user_id}")
async def update_member(course_id: uuid.UUID, user_id: uuid.UUID, body: MemberUpdate, db: AsyncSession = Depends(get_db),
                        user: User = Depends(get_current_user)):
    access.require_admin(user)
    _, role = await access.load_course(db, user, course_id, access.COURSE_STAFF)
    m = (await db.execute(select(CourseMember).where(
        CourseMember.course_id == course_id, CourseMember.user_id == user_id))).scalar_one_or_none()
    if m is None:
        raise HTTPException(status_code=404, detail="Member not found")
    if body.role and body.role != m.role:
        if role != "teacher":
            raise HTTPException(status_code=403, detail="Only the course teacher can change roles")
        if m.role == "teacher" and body.role != "teacher":
            teachers = (await db.execute(select(func.count()).where(
                CourseMember.course_id == course_id, CourseMember.role == "teacher"))).scalar_one()
            if teachers <= 1:
                raise HTTPException(status_code=409, detail="A course needs at least one teacher")
        m.role = body.role
        m.role_locked = True
    if body.unlock_role:
        m.role_locked = False
    if body.clear_group:
        m.group_id = None
    elif body.group_id:
        m.group_id = body.group_id
    await db.commit()
    await observability.activity("member_update", member=user_id, role=body.role, unlock=body.unlock_role or None)
    return {"ok": True}


@router.delete("/courses/{course_id}/members/{user_id}", status_code=204)
async def remove_member(course_id: uuid.UUID, user_id: uuid.UUID, db: AsyncSession = Depends(get_db),
                        user: User = Depends(get_current_user)):
    access.require_admin(user)
    _, role = await access.load_course(db, user, course_id, access.COURSE_STAFF)
    m = (await db.execute(select(CourseMember).where(
        CourseMember.course_id == course_id, CourseMember.user_id == user_id))).scalar_one_or_none()
    if m is None:
        return
    if m.role != "student" and role != "teacher":
        raise HTTPException(status_code=403, detail="Only the course teacher can remove staff")
    if m.role == "teacher":
        teachers = (await db.execute(select(func.count()).where(
            CourseMember.course_id == course_id, CourseMember.role == "teacher"))).scalar_one()
        if teachers <= 1:
            raise HTTPException(status_code=409, detail="A course needs at least one teacher")
    await db.delete(m)
    await db.commit()
    await observability.activity("member_remove", member=user_id)


