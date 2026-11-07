"""
Subjects (предмети) — FINKI's subjects, with the practice tasks, the person's courses and their AI practice in each.

  GET    /subjects                     every subject: tasks to practise, how many I finished, my courses of it
  GET    /subjects/{id}                one subject: its practice tasks, my courses, my AI practice tasks
  POST   /subjects/{id}/practice       AI makes a new practice task for me (needs my own AI key — profile)
  DELETE /practice/{task_id}           forget one of my AI practice tasks
  POST   /admin/subjects               admin: add a subject; PUT / DELETE /admin/subjects/{id}
  GET    /subjects/{id}/student-practice  staff of the subject: what the students practise there with their own AI key
  GET    /practice/{task_id}/work      staff of the subject: the student's work on one of their AI practice tasks
Electives in a student's own semesters: routers/electives.py (the admin only adds subjects to the catalogue).
"""
import uuid
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import access
from app.core.deps import get_current_admin, get_current_user
from app.core.language import Lang, get_language
from app.database import get_db
from app.models.course import Course, CourseMember
from app.models.electives import ElectiveChoice
from app.models.session import Session
from app.models.task import Subject, Task
from app.models.user import User
from app.schemas.task import LANGUAGES
from app.services import ai_config, content, limits, observability, practice

router = APIRouter(tags=["subjects"])


def _name(s: Subject, lang: str | None) -> str:
    return (s.name_en or s.name) if lang == "en" else s.name


def _subject_out(s: Subject, lang: str | None) -> dict:
    return {"id": str(s.id), "code": s.code, "finki_code": s.finki_code, "name": _name(s, lang), "name_mk": s.name, "name_en": s.name_en,
            "semester": s.semester, "elective": bool(s.elective), "languages": s.languages or [], "icon": s.icon, "color": s.color,
            "description": s.description}


def _practice_tasks_q(user: User, staff: bool = False):
    """Tasks to practise: public code tasks (staff also see course-only ones); never someone's AI practice."""
    q = select(Task).where(Task.kind == "code", Task.generated_for.is_(None))
    if not (staff or access.is_staff(user)):
        q = q.where(Task.is_public.is_(True))
    return q


async def _my_courses(db: AsyncSession, user: User) -> list[tuple[Course, str]]:
    if user.role == "admin":
        return [(c, "teacher") for c in (await db.execute(select(Course).where(Course.archived.is_(False)))).scalars()]
    return list((await db.execute(select(Course, CourseMember.role).join(CourseMember, CourseMember.course_id == Course.id)
                                  .where(CourseMember.user_id == user.id, Course.archived.is_(False)))).all())


def _course_brief(c: Course, role: str) -> dict:
    return {"id": str(c.id), "code": c.code, "name": c.name, "semester": c.semester, "my_role": role}


@router.get("/subjects")
async def list_subjects(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user),
                        lang: Optional[Lang] = Depends(content.reader_language)):
    subjects = (await db.execute(select(Subject).order_by(Subject.semester.is_(None), Subject.semester,
                                                          Subject.position, Subject.name))).scalars().all()
    tq = _practice_tasks_q(user).subquery()
    counts = dict((await db.execute(select(tq.c.subject_id, func.count()).group_by(tq.c.subject_id))).all())
    done = dict((await db.execute(
        select(Task.subject_id, func.count(func.distinct(Session.task_id))).join(Session, Session.task_id == Task.id)
        .where(Session.user_id == user.id, Session.status == "completed").group_by(Task.subject_id))).all())
    generated = dict((await db.execute(select(Task.subject_id, func.count()).where(Task.generated_for == user.id)
                                       .group_by(Task.subject_id))).all())
    mine_el = {c.subject_id: c.semester for c in (await db.execute(
        select(ElectiveChoice).where(ElectiveChoice.user_id == user.id))).scalars()}
    courses: dict = {}
    for c, role in await _my_courses(db, user):
        if c.subject_id:
            courses.setdefault(c.subject_id, []).append(_course_brief(c, role))
    out = []
    for s in subjects:
        out.append({**_subject_out(s, lang), "tasks": counts.get(s.id, 0), "done": done.get(s.id, 0),
                    "generated": generated.get(s.id, 0), "courses": courses.get(s.id, []),
                    "my_semester": mine_el.get(s.id)})   # a student's chosen elective: the semester they put it in
    return {"subjects": out, "unsorted": counts.get(None, 0), "can_practice": ai_config.personal() is not None}


async def _subject(db: AsyncSession, subject_id) -> Subject:
    s = (await db.execute(select(Subject).where(Subject.id == subject_id))).scalar_one_or_none()
    if s is None:
        raise HTTPException(status_code=404, detail="Subject not found")
    return s


def _task_item(t: Task, lang, progress: dict) -> dict:
    p = progress.get(t.id)
    return {"id": str(t.id), "title": content.title(t, lang), "language": t.language, "created_at": t.created_at.isoformat(),
            "status": p[0] if p else None, "current_step": p[1] if p else None, "is_public": t.is_public}


@router.get("/subjects/{subject_id}")
async def subject_detail(subject_id: uuid.UUID, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user),
                         lang: Optional[Lang] = Depends(content.reader_language)):
    s = await _subject(db, subject_id)
    staff = await access.subject_staff(db, user, s.id)
    tasks = (await db.execute(_practice_tasks_q(user, staff).where(Task.subject_id == s.id).order_by(Task.created_at))).scalars().all()
    mine = (await db.execute(select(Task).where(Task.generated_for == user.id, Task.subject_id == s.id)
                             .order_by(Task.created_at.desc()))).scalars().all()
    ids = [t.id for t in [*tasks, *mine]]
    progress: dict = {}
    if ids:
        for sess in (await db.execute(select(Session).where(Session.user_id == user.id, Session.task_id.in_(ids))
                                      .order_by(Session.updated_at))).scalars():
            # completed wins over a later restarted session
            if progress.get(sess.task_id, ("",))[0] != "completed":
                progress[sess.task_id] = (sess.status, sess.current_step)
    courses = [_course_brief(c, role) for c, role in await _my_courses(db, user) if c.subject_id == s.id]
    return {**_subject_out(s, lang), "tasks": [_task_item(t, lang, progress) for t in tasks],
            "generated": [_task_item(t, lang, progress) for t in mine], "courses": courses,
            "can_practice": ai_config.personal() is not None, "staff": staff}


class PracticeIn(BaseModel):
    language: str
    level: Literal["easy", "medium", "hard"] = "medium"
    topic: str = Field("", max_length=300)


@router.post("/subjects/{subject_id}/practice", status_code=201)
async def new_practice_task(subject_id: uuid.UUID, body: PracticeIn, db: AsyncSession = Depends(get_db),
                            user: User = Depends(limits.limit_ai), lang: Lang = Depends(get_language)):
    """AI writes a whole new task (text, starting code, solution, tests) for me in this subject — on my own key."""
    if ai_config.personal() is None:
        raise HTTPException(status_code=403, detail="Add your own AI key in your profile to practise with AI")
    s = await _subject(db, subject_id)
    if body.language not in (s.languages or []) or body.language not in LANGUAGES:
        raise HTTPException(status_code=422, detail="This subject has no tasks in that language")
    task = await practice.generate(db, user, s, body.language, body.level, body.topic, lang)
    observability.set_context(task_id=task.id)
    await observability.activity("practice_generate", subject_id=s.id, title=task.title, language=body.language, level=body.level)
    return {"task_id": str(task.id), "title": task.title}


@router.delete("/practice/{task_id}", status_code=204)
async def delete_practice_task(task_id: uuid.UUID, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    t = (await db.execute(select(Task).where(Task.id == task_id, Task.generated_for == user.id))).scalar_one_or_none()
    if t is None:
        raise HTTPException(status_code=404, detail="Task not found")
    await db.execute(delete(Session).where(Session.task_id == t.id))
    await db.delete(t)
    await db.commit()


class SubjectIn(BaseModel):
    code: str = Field(min_length=1, max_length=20)
    finki_code: Optional[str] = Field(None, max_length=20)   # the official code, e.g. F23L1W020
    name: str = Field(min_length=1, max_length=200)
    name_en: str = Field("", max_length=200)
    semester: Optional[int] = Field(None, ge=1, le=8)
    elective: bool = False   # an elective; with a semester it is listed both there and under "Electives"
    languages: list[str] = Field(default_factory=list, max_length=20)
    icon: str = Field("book-open", max_length=40)
    color: str = Field("#2747C9", pattern=r"^#[0-9A-Fa-f]{6}$")
    description: str = Field("", max_length=5000)


async def _check_finki(db: AsyncSession, code: Optional[str], own_id) -> None:
    code = (code or "").strip()
    if code and (await db.execute(select(Subject.id).where(Subject.finki_code == code, Subject.id != own_id))).first():
        raise HTTPException(status_code=409, detail="A subject with this code already exists")


def _check_langs(langs: list[str]) -> list[str]:
    bad = [x for x in langs if x not in LANGUAGES]
    if bad:
        raise HTTPException(status_code=422, detail="Unknown language")
    return list(dict.fromkeys(langs))


@router.post("/admin/subjects", status_code=201)
async def create_subject(body: SubjectIn, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_admin)):
    if (await db.execute(select(Subject.id).where(Subject.code == body.code.strip()))).first():
        raise HTTPException(status_code=409, detail="A subject with this code already exists")
    pos = (await db.execute(select(func.coalesce(func.max(Subject.position), 0)))).scalar_one() + 1
    await _check_finki(db, body.finki_code, None)
    s = Subject(**{**body.model_dump(), "code": body.code.strip(), "finki_code": (body.finki_code or "").strip() or None,
                   "languages": _check_langs(body.languages),
                   "elective": body.elective or body.semester is None}, position=pos)
    db.add(s)
    await db.commit()
    await observability.activity("subject_create", subject_id=s.id, code=s.code, name=s.name)
    return _subject_out(s, "mk")


@router.put("/admin/subjects/{subject_id}")
async def update_subject(subject_id: uuid.UUID, body: SubjectIn, db: AsyncSession = Depends(get_db),
                         _: User = Depends(get_current_admin)):
    s = await _subject(db, subject_id)
    if (await db.execute(select(Subject.id).where(Subject.code == body.code.strip(), Subject.id != s.id))).first():
        raise HTTPException(status_code=409, detail="A subject with this code already exists")
    await _check_finki(db, body.finki_code, s.id)
    for k, v in body.model_dump().items():
        setattr(s, k, _check_langs(v) if k == "languages" else v.strip() if k == "code" else v)
    s.finki_code = (body.finki_code or "").strip() or None
    s.elective = body.elective or body.semester is None
    await db.commit()
    await observability.activity("subject_update", subject_id=s.id, code=s.code, name=s.name)
    return _subject_out(s, "mk")


@router.delete("/admin/subjects/{subject_id}", status_code=204)
async def delete_subject(subject_id: uuid.UUID, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_admin)):
    s = await _subject(db, subject_id)
    code, name = s.code, s.name
    await db.delete(s)  # tasks and courses keep existing, without a subject
    await db.commit()
    await observability.activity("subject_delete", subject_id=subject_id, code=code, name=name)


# ---------------------------------------------------------------------------
# Staff of a subject: what the students practise there with their own AI key
# ---------------------------------------------------------------------------

@router.get("/subjects/{subject_id}/student-practice")
async def student_practice(subject_id: uuid.UUID, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user),
                           lang: Optional[Lang] = Depends(content.reader_language)):
    """Every student's AI practice tasks in this subject (made with their own key), with how far they got."""
    s = await _subject(db, subject_id)
    if not await access.subject_staff(db, user, s.id):
        raise HTTPException(status_code=403, detail="Course staff access required")
    rows = (await db.execute(select(Task, User).join(User, User.id == Task.generated_for).where(
        Task.subject_id == s.id, Task.generated_for.is_not(None)).order_by(User.name, Task.created_at.desc()))).all()
    progress: dict = {}
    if rows:
        for sess in (await db.execute(select(Session).where(Session.task_id.in_([t.id for t, _ in rows]))
                                      .order_by(Session.updated_at))).scalars():
            if sess.user_id and progress.get(sess.task_id, ("",))[0] != "completed":
                progress[sess.task_id] = (sess.status, sess.current_step)
    students: dict = {}
    for t, u in rows:
        st = students.setdefault(u.id, {"user_id": str(u.id), "name": u.name, "email": u.email, "tasks": []})
        st["tasks"].append({**_task_item(t, lang, progress), "level": None})
    out = list(students.values())
    for st in out:
        st["done"] = sum(1 for x in st["tasks"] if x["status"] == "completed")
    return {"students": out, "tasks": len(rows)}


@router.get("/practice/{task_id}/work")
async def practice_work(task_id: uuid.UUID, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    """The student's latest work on one of their AI practice tasks: status, steps and code (staff of the subject)."""
    t = (await db.execute(select(Task).where(Task.id == task_id, Task.generated_for.is_not(None)))).scalar_one_or_none()
    if t is None:
        raise HTTPException(status_code=404, detail="Task not found")
    if not await access.subject_staff(db, user, t.subject_id):
        raise HTTPException(status_code=403, detail="Course staff access required")
    sess = (await db.execute(select(Session).where(Session.task_id == t.id, Session.user_id == t.generated_for)
                             .order_by(Session.updated_at.desc()).limit(1))).scalar_one_or_none()
    student = (await db.execute(select(User).where(User.id == t.generated_for))).scalar_one()
    steps = []
    if sess is not None:
        from app.models.session import SessionStep
        steps = [{"n": x.step_number, "title": x.title, "status": x.status} for x in (await db.execute(
            select(SessionStep).where(SessionStep.session_id == sess.id).order_by(SessionStep.step_number))).scalars()]
    return {"task_id": str(t.id), "title": t.title, "language": t.language,
            "student": {"user_id": str(student.id), "name": student.name, "email": student.email},
            "status": sess.status if sess else None, "code": sess.current_code if sess else "",
            "updated_at": sess.updated_at.isoformat() + "Z" if sess else None, "steps": steps}
