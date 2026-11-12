"""
Subject spaces ("courses" in the code): every subject has one, made automatically (services/spaces.py) — nobody
makes or deletes them by hand. Members: students (from their study plan, the admin or Moodle) and teachers with
the permissions the admin gave them (core/permissions.py).

Routes
  /courses                       the spaces I am in (the admin: all)
  /courses/{id}                  details (+ the assignments I can see, my permissions); settings (admin)
  /courses/{id}/groups           groups (admin)
  /courses/{id}/members          list (people.view); add by e-mail, permissions / group, remove (admin)
  /admin/courses                 admin: every space with its teachers and their permissions

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
from app.core import permissions as P
from app.services import content, observability, spaces

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
    # (the subject of a space never changes: every subject has its own one)


class JoinIn(BaseModel):
    code: str


class GroupIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    language: Optional[Literal["mk", "en"]] = None  # teaching language of the group (None = the course's)


Template = Literal["professor", "assistant", "lab"]


class MembersIn(BaseModel):
    emails: list[str] = Field(min_length=1, max_length=1000)
    # student | teacher; the old role names ("lab", "assistant") are a teacher with that template's permissions
    role: Literal["student", "teacher", "professor", "assistant", "lab"] = "student"
    permissions: Optional[list[str]] = None   # a teacher's permissions (default: the template, or all for "teacher")
    group_id: Optional[uuid.UUID] = None


def _who(role: str, perms: Optional[list[str]]) -> tuple[str, list[str]]:
    """(role, permissions) of a membership from what the admin sent."""
    if role == "student":
        return "student", []
    if perms is not None:
        return "teacher", P.clean(perms)
    return "teacher", P.template(role if role != "teacher" else "professor")


class MemberUpdate(BaseModel):
    role: Optional[Literal["student", "teacher", "professor", "assistant", "lab"]] = None
    permissions: Optional[list[str]] = None
    group_id: Optional[uuid.UUID] = None
    clear_group: bool = False
    unlock_role: bool = False   # let Moodle (LTI) set this person's role again


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _course_out(c: Course, role, students: int = 0) -> dict:
    staff = role in access.COURSE_STAFF
    perms = sorted(getattr(role, "perms", ())) if staff else []
    return {
        "id": str(c.id), "code": c.code, "name": c.name, "semester": c.semester, "description": c.description,
        "archived": c.archived, "my_role": str(role), "students": students,
        "permissions": [p for p in P.ALL if p in perms], "template": P.template_of(perms) if staff else None,
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
        rows = [(c, access.Role("teacher", P.ALL)) for c in (await db.execute(select(Course).order_by(Course.name))).scalars()]
    else:
        rows = [(c, access.Role("teacher", m.permissions or ()) if m.role == "teacher" else access.Role("student"))
                for c, m in (await db.execute(
                    select(Course, CourseMember).join(CourseMember, CourseMember.course_id == Course.id)
                    .where(CourseMember.user_id == user.id).order_by(Course.name))).all()]
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


@router.post("/courses", status_code=410)
async def create_course(user: User = Depends(get_current_user)):
    """There are no courses to make: every subject has its own space."""
    raise HTTPException(status_code=410, detail="Every subject has its own space; courses are not made by hand")


@router.delete("/courses/{course_id}", status_code=410)
async def delete_course(course_id: uuid.UUID, user: User = Depends(get_current_user)):
    raise HTTPException(status_code=410, detail="A subject's space goes only with its subject")


@router.get("/admin/courses")
async def admin_courses(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    """Admin: every subject's space with its teachers (and their permissions) and how many students it has."""
    access.require_admin(user)
    courses = (await db.execute(select(Course).order_by(Course.name))).scalars().all()
    people = (await db.execute(select(CourseMember, User).join(User, User.id == CourseMember.user_id))).all()
    teachers: dict = {}
    students: dict = {}
    for m, u in people:
        if m.role == "teacher":
            teachers.setdefault(str(m.course_id), []).append({
                "user_id": str(u.id), "name": u.name, "email": u.email, "permissions": P.clean(m.permissions),
                "template": P.template_of(P.clean(m.permissions))})
        else:
            students[str(m.course_id)] = students.get(str(m.course_id), 0) + 1
    return [{**_course_out(c, access.Role("teacher", P.ALL), students.get(str(c.id), 0)),
             "teachers": sorted(teachers.get(str(c.id), []), key=lambda x: x["name"])} for c in courses]


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

    out_assignments = await assignments.assignments_for_course(db, course, user, role in access.COURSE_GRADERS, role=role)

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
    for k, v in body.model_dump(exclude_none=True).items():
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
    await access.load_course(db, user, course_id, "people.view")
    groups = await _groups_map(db, course_id)
    rows = (await db.execute(
        select(CourseMember, User).join(User, User.id == CourseMember.user_id)
        .where(CourseMember.course_id == course_id).order_by(CourseMember.role.desc(), User.name)
    )).all()
    return [{"user_id": str(u.id), "name": u.name, "email": u.email, "role": m.role,
             "permissions": P.clean(m.permissions) if m.role == "teacher" else [],
             "template": P.template_of(P.clean(m.permissions)) if m.role == "teacher" else None,
             "source": m.source, "account": u.role,
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
    new_role, perms = _who(body.role, body.permissions)

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
            if new_role == "teacher" or m.role == "student":   # e.g. someone Moodle brought in gets their real place
                m.role, m.permissions = new_role, perms
                if new_role == "student":
                    m.source = "admin"
            m.role_locked = True
            continue
        # what the admin gives is locked: Moodle (LTI) doesn't change it
        db.add(CourseMember(course_id=course_id, user_id=u.id, role=new_role, permissions=perms, group_id=body.group_id,
                            role_locked=True, source="admin"))
        added.append(e)
    await db.commit()
    await observability.activity("members_add", role=new_role, template=P.template_of(perms) if perms else None,
                                 added=len(added), already=len(already) or None,
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
    if body.role is not None or body.permissions is not None:
        new_role, perms = _who(body.role or m.role, body.permissions)
        if body.role is None and body.permissions is not None:
            new_role = "teacher"
        m.role, m.permissions = new_role, perms
        if new_role == "student":
            m.source = "admin"
        m.role_locked = True
    if body.unlock_role:
        m.role_locked = False
    if body.clear_group:
        m.group_id = None
    elif body.group_id:
        m.group_id = body.group_id
    await db.commit()
    await observability.activity("member_update", member=user_id, role=m.role,
                                 permissions=len(m.permissions or []) if m.role == "teacher" else None,
                                 unlock=body.unlock_role or None)
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
    await db.delete(m)
    await db.commit()
    await observability.activity("member_remove", member=user_id)


