"""
Assignments (labs / homework / exams), submissions, exam attempts, manual grading, similarity, gradebook.

Routes
  POST /courses/{id}/assignments                 staff: create
  GET  /courses/{id}/gradebook(.csv)             staff: students x assignments (final points)
  GET  /assignments/{id}                         details (students: their variant, their exam state, their points)
  PUT/DELETE /assignments/{id}                   staff
  POST /assignments/{id}/start | finish          student: exam attempt (personal timer, allowed networks)
  POST /assignments/{id}/events                  student: exam signals (left the tab, large paste)
  POST /assignments/{id}/tasks/{tid}/submit      run all tests, score, keep
  GET  /assignments/{id}/submissions             own submissions (staff: anyone's)
  GET  /assignments/{id}/overview                staff: every student — points, attempt, signals
  GET  /assignments/{id}/review                  staff: one student's task — submissions, grade, line comments
  PUT  /assignments/{id}/grades                  staff: adjust / override points, comment
  POST /submissions/{sid}/comments, DELETE /comments/{cid}   staff: line comments
  POST /assignments/{id}/publish                 staff: show points & comments to students
  GET  /assignments/{id}/feedback                student: own graded work (after publishing)
  GET  /assignments/{id}/similarity              staff: similar solutions (plagiarism check)
"""
import csv
import io
import uuid
from datetime import datetime, timezone
from typing import Literal, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Query, Request, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import access
from app.core.deps import get_current_user
from app.database import get_db
from app.models.course import (ATTENDANCE, Assignment, AssignmentAttempt, AssignmentTask, Attendance, CodeComment,
                               Course, CourseGroup, CourseMember, ExamEvent, Submission, SubmissionFile, TaskGrade)
from app.models.task import DiagramUpload, TaskFile
from app.models.task import Task
from app.schemas.task import TaskListItem
from app.models.user import User
from app.config import settings
from app.database import AsyncSessionLocal
from app.services import content, diagrams, emails, exam, standing, observability, similarity, submission_queue, uploads

router = APIRouter(tags=["assignments"], dependencies=[Depends(content.use_language)])


def _utc_naive(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    return dt.astimezone(timezone.utc).replace(tzinfo=None) if dt.tzinfo else dt


def _iso(dt: Optional[datetime]) -> Optional[str]:
    return dt.replace(tzinfo=timezone.utc).isoformat() if dt else None


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class AssignmentTaskIn(BaseModel):
    task_id: uuid.UUID
    points: float = Field(10, ge=0, le=1000)
    variant_group: Optional[int] = Field(None, ge=1, le=50)


class AssignmentIn(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    description: str = ""
    kind: Literal["lab", "homework", "practice", "exam"] = "lab"
    group_id: Optional[uuid.UUID] = None
    opens_at: Optional[datetime] = None
    due_at: Optional[datetime] = None
    allow_late: bool = False
    late_penalty: int = Field(0, ge=0, le=100)
    published: bool = False
    tasks: list[AssignmentTaskIn] = Field(default_factory=list, max_length=50)
    # sprint 4
    ai_mode: Literal["full", "hints", "off"] = "full"
    hint_limit: int = Field(3, ge=0, le=50)
    exam: bool = False
    duration_minutes: Optional[int] = Field(None, ge=1, le=24 * 60)
    allowed_ips: str = Field("", max_length=2000)
    results_visibility: Literal["full", "summary", "none"] = "full"
    scores_after_publish: bool = False
    # sprint 5
    review_threshold: int = Field(85, ge=0, le=100)
    improve_limit: int = Field(2, ge=0, le=20)
    # sprint 7: which part of the final grade it counts towards (None = by kind)
    category: Optional[Literal["labs", "homework", "k1", "k2", "exam", "none"]] = None
    # sprint 19: a practice assignment that prepares for a colloquium / the exam (feeds the estimated grade)
    practice_for: Optional[Literal["k1", "k2", "exam"]] = None
    # sprint 8: compiler errors shown in the editor while typing
    editor_checks: bool = True

    @field_validator("due_at")
    @classmethod
    def _due_after_open(cls, v, info):
        opens = info.data.get("opens_at")
        if v and opens and _utc_naive(v) <= _utc_naive(opens):
            raise ValueError("due_at must be after opens_at")
        return v

    @field_validator("allowed_ips")
    @classmethod
    def _ips(cls, v):
        try:
            exam.parse_networks(v)
        except ValueError:
            raise ValueError("allowed_ips must be IP addresses or networks like 194.149.135.0/24")
        return v.strip()


class SubmitIn(BaseModel):
    code: str = Field(max_length=200_000)
    # diagram tasks: the picture/PDF the diagram was read from (kept with the submission for the teacher)
    upload_id: Optional[uuid.UUID] = None


class EventIn(BaseModel):
    kind: Literal["blur", "focus", "paste"]
    task_id: Optional[uuid.UUID] = None
    detail: str = Field("", max_length=500)


class GradeIn(BaseModel):
    user_id: uuid.UUID
    task_id: uuid.UUID
    adjust: float = Field(0, ge=-1000, le=1000)
    override: Optional[float] = Field(None, ge=0, le=1000)
    comment: str = Field("", max_length=5000)
    rubric_scores: Optional[dict[str, float]] = None  # {criterion id: points}; sets the points of a rubric task


class CommentIn(BaseModel):
    line: int = Field(ge=1, le=100_000)
    body: str = Field(min_length=1, max_length=5000)
    path: str = Field("", max_length=500)  # a file inside a project zip


class AttendanceIn(BaseModel):
    user_id: uuid.UUID
    status: Optional[Literal["present", "absent", "excused"]] = None  # None = clear


class PublishIn(BaseModel):
    published: bool = True


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def status_of(a: Assignment, now: datetime) -> str:
    if not a.published:
        return "draft"
    if a.opens_at and a.opens_at > now:
        return "scheduled"
    if a.due_at and a.due_at <= now:
        return "late" if a.allow_late and not a.exam else "closed"
    return "open"


async def _task_rows(db: AsyncSession, a: Assignment) -> list[tuple[AssignmentTask, Task]]:
    return (await db.execute(
        select(AssignmentTask, Task).join(Task, Task.id == AssignmentTask.task_id)
        .where(AssignmentTask.assignment_id == a.id).order_by(AssignmentTask.order)
    )).all()


def _rows_for_student(rows, a: Assignment, user_id) -> list[tuple[AssignmentTask, Task]]:
    chosen = {at.id for at in exam.tasks_for_student([at for at, _ in rows], a.id, user_id)}
    return [(at, t) for at, t in rows if at.id in chosen]


async def _groups_map(db: AsyncSession, course_id) -> dict:
    rows = (await db.execute(select(CourseGroup).where(CourseGroup.course_id == course_id))).scalars().all()
    return {str(g.id): g.name for g in rows}


async def load_assignment(db: AsyncSession, user: User, assignment_id, staff_only: bool = False, graders: bool = False):
    """(assignment, course role). Students only get assignments that are open to them. `staff_only`: teachers and
    assistants; with `graders` also a лаборант (lab) — but a лаборант only ever gets labs / practice."""
    a = (await db.execute(select(Assignment).where(Assignment.id == assignment_id))).scalar_one_or_none()
    if a is None:
        raise HTTPException(status_code=404, detail="Assignment not found")
    roles = (access.COURSE_GRADERS if graders else access.COURSE_STAFF) if staff_only else None
    _, role = await access.load_course(db, user, a.course_id, roles)
    if not access.lab_may_see(role, a.kind):
        raise HTTPException(status_code=404, detail="Assignment not found")
    if role == "student":
        m = await access.membership(db, user, a.course_id)
        if not access.assignment_open(a) or (a.group_id and m.group_id != a.group_id):
            raise HTTPException(status_code=404, detail="Assignment not found")
    return a, role


async def best_ratios(db: AsyncSession, a: Assignment, user_ids: list) -> dict:
    """{(user_id, task_id): (passed, total)} of each student's best tested submission (by share of passed tests)."""
    if not user_ids:
        return {}
    rows = (await db.execute(select(Submission.user_id, Submission.task_id, Submission.passed, Submission.total).where(
        Submission.assignment_id == a.id, Submission.user_id.in_(user_ids), Submission.status == "done",
        Submission.total > 0))).all()
    out: dict = {}
    for uid, tid, p, t in rows:
        k = (str(uid), str(tid))
        if k not in out or p / t > out[k][0] / out[k][1]:
            out[k] = (p, t)
    return out


def _ratio_flag(a: Assignment, pt) -> bool:
    """Best submission passes most (≥ threshold) but not all tests: "more points possible", worth a teacher's look."""
    if not pt:
        return False
    best = pt
    return more_points(a, best[0], best[1])


def _settings_out(a: Assignment, staff: bool) -> dict:
    out = {
        "ai_mode": a.ai_mode, "hint_limit": a.hint_limit, "exam": a.exam, "duration_minutes": a.duration_minutes,
        "results_visibility": a.results_visibility, "scores_after_publish": a.scores_after_publish,
        "grades_published": a.grades_published, "ip_restricted": bool(a.allowed_ips.strip()),
        "review_threshold": a.review_threshold, "improve_limit": a.improve_limit,
        "category": a.category, "counts_as": standing.category_of(a), "editor_checks": a.editor_checks,
        "practice_for": a.practice_for,
    }
    if staff:
        out["allowed_ips"] = a.allowed_ips
    return out


async def assignment_out(db: AsyncSession, a: Assignment, user: User, staff: bool, now: datetime,
                         groups: dict, request: Request | None = None) -> dict:
    """The assignment as the user may see it. Students: only their task variants; for an exam that they have not
    started, no tasks at all; points only when the teacher lets them see points."""
    rows = await _task_rows(db, a)
    out = {
        "id": str(a.id), "course_id": str(a.course_id), "title": a.title, "description": a.description,
        "kind": a.kind, "group_id": str(a.group_id) if a.group_id else None,
        "group_name": groups.get(str(a.group_id)) if a.group_id else None,
        "opens_at": _iso(a.opens_at), "due_at": _iso(a.due_at), "allow_late": a.allow_late,
        "late_penalty": a.late_penalty, "published": a.published, "status": status_of(a, now),
        **_settings_out(a, staff),
    }
    if staff:
        out["tasks"] = [{"task_id": str(t.id), "title": content.t_title(t), "language": t.language, "points": at.points,
                         "variant_group": at.variant_group, "kind": t.kind, "rubric": bool(t.rubric)} for at, t in rows]
        out["max_points"] = exam.max_points([at for at, _ in rows])
        return out

    mine = _rows_for_student(rows, a, user.id)
    out["max_points"] = sum(at.points for at, _ in mine)
    if a.exam:
        att = await exam.attempt_of(db, a, user)
        out["exam_state"] = exam.exam_state(a, att, now)
        out["attempt"] = None if att is None else {
            "started_at": _iso(att.started_at), "ends_at": _iso(att.ends_at), "finished_at": _iso(att.finished_at)}
        if request is not None and a.allowed_ips.strip():
            out["ip_ok"] = exam.ip_allowed(a, exam.client_ip(request))
        if att is None:
            out["tasks"], out["task_count"], out["my_score"] = [], len(mine), None
            return out

    best = await exam.best_scores(db, [a.id], [user.id])
    grades = await exam.grades_map(db, [a.id], [user.id])
    ratios = await best_ratios(db, a, [user.id])
    visible = exam.scores_visible(a)
    tasks, total, any_score = [], 0.0, False
    for at, t in mine:
        b = best.get((str(a.id), str(user.id), str(t.id)))
        g = grades.get((str(a.id), str(user.id), str(t.id)))
        final = exam.final_points(b[0] if b else None, g, at.points, auto=t.kind == "code")
        if final is not None:
            total += final
            any_score = True
        tasks.append({"task_id": str(t.id), "title": content.t_title(t), "language": t.language, "points": at.points,
                      "kind": t.kind,
                      "my_score": final if visible else None, "my_late": bool(b[1]) if b else False,
                      "my_submissions": b[2] if b else 0,
                      "more_points": a.results_visibility != "none" and g is None
                                     and _ratio_flag(a, ratios.get((str(user.id), str(t.id)))),
                      "has_feedback": a.grades_published and bool(g and (g.comment or g.adjust or g.override is not None
                                                                          or g.rubric_scores))})
    out["tasks"] = tasks
    out["my_score"] = round(total, 2) if visible and any_score else None
    return out


async def assignments_for_course(db: AsyncSession, course: Course, user: User, staff: bool, lab_only: bool = False) -> list[dict]:
    groups = await _groups_map(db, course.id)
    now = datetime.utcnow()
    q = select(Assignment).where(Assignment.course_id == course.id)
    if not staff:
        q = q.where(access.visible_to_student_clause(user, now))
    elif lab_only:
        q = q.where(Assignment.kind.in_(access.LAB_KINDS))
    assignments = (await db.execute(
        q.order_by(Assignment.due_at.is_(None), Assignment.due_at, Assignment.created_at))).scalars().all()
    return [await assignment_out(db, a, user, staff, now, groups) for a in assignments]


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------

async def _save(db: AsyncSession, a: Assignment, body: AssignmentIn) -> None:
    if body.group_id and not (await db.execute(select(CourseGroup.id).where(
            CourseGroup.id == body.group_id, CourseGroup.course_id == a.course_id))).first():
        raise HTTPException(status_code=422, detail="Group not found")
    task_ids = [t.task_id for t in body.tasks]
    if len(set(task_ids)) != len(task_ids):
        raise HTTPException(status_code=422, detail="A task appears twice in the assignment")
    found = set((await db.execute(select(Task.id).where(Task.id.in_(task_ids)))).scalars()) if task_ids else set()
    if found != set(task_ids):
        raise HTTPException(status_code=422, detail="Task not found")
    a.title, a.description = body.title.strip(), body.description
    a.kind = body.kind
    a.exam = body.exam or body.kind == "exam"
    a.group_id = body.group_id
    a.opens_at, a.due_at = _utc_naive(body.opens_at), _utc_naive(body.due_at)
    a.allow_late = body.allow_late and not a.exam
    a.late_penalty = body.late_penalty if a.allow_late else 0
    a.published = body.published
    a.ai_mode, a.hint_limit = body.ai_mode, body.hint_limit
    a.duration_minutes = body.duration_minutes if a.exam else None
    a.allowed_ips = body.allowed_ips
    a.results_visibility = body.results_visibility
    a.scores_after_publish = body.scores_after_publish
    a.review_threshold, a.improve_limit = body.review_threshold, body.improve_limit
    a.category = body.category
    # preparation for a colloquium / the exam: only practice assignments, and they never count in the grade
    a.practice_for = body.practice_for if body.kind == "practice" else None
    if a.practice_for:
        a.category = "none"
    a.editor_checks = body.editor_checks
    await db.flush()
    await db.execute(delete(AssignmentTask).where(AssignmentTask.assignment_id == a.id))
    for i, t in enumerate(body.tasks):
        db.add(AssignmentTask(assignment_id=a.id, task_id=t.task_id, points=t.points, order=i, variant_group=t.variant_group))


async def _draft_after_save(db: AsyncSession, course, a: Assignment, user: User, was_published: bool, old_due) -> None:
    """Prepare (never send) an e-mail draft: a newly published assignment, or a moved deadline of a published one."""
    if not a.published:
        return
    if not was_published:
        await emails.draft(db, course, "announcement", a, user)
    elif a.due_at != old_due:
        await emails.draft(db, course, "deadline", a, user)


def _lab_limits(role: str, body: "AssignmentIn") -> None:
    """A лаборант makes and edits only labs and practice, counted (if at all) as labs."""
    if role == "lab" and (body.kind not in access.LAB_KINDS or body.category not in access.LAB_CATEGORIES or body.exam):
        raise HTTPException(status_code=403, detail="A лаборант makes only labs and practice")


@router.get("/courses/{course_id}/task-bank", response_model=list[TaskListItem])
async def course_task_bank(course_id: uuid.UUID, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user),
                           lang: Optional[str] = Depends(content.reader_language)):
    """The task bank for whoever makes the course's assignments (a лаборант has no access to the admin bank)."""
    await access.load_course(db, user, course_id, access.ASSIGNMENT_AUTHORS)
    rows = (await db.execute(select(Task).where(Task.generated_for.is_(None)).order_by(Task.created_at))).scalars().all()
    return [TaskListItem.model_validate(t).model_copy(update={"title": content.title(t, lang)}) for t in rows]


class GenerateIn(BaseModel):
    language: str
    level: Literal["easy", "medium", "hard"] = "medium"
    topic: str = Field("", max_length=300)
    count: int = Field(1, ge=1, le=3)
    type: Literal["tests", "project"] = "tests"   # with automatic tests, or a project handed in as a zip


@router.post("/courses/{course_id}/generate-tasks", status_code=201)
async def generate_tasks(course_id: uuid.UUID, body: GenerateIn, db: AsyncSession = Depends(get_db),
                         user: User = Depends(get_current_user), lang: Optional[str] = Depends(content.use_language)):
    """The tutor writes new tasks for the course's subject (colloquium exercises, labs): with tests that the AI's own
    solution must pass, or a project (zip) with a rubric and a reference solution. They go into the task bank (not
    public) and the form adds them to the assignment. For the professor, assistants and лаборанти."""
    from app.models.task import Subject
    from app.schemas.task import LANGUAGES
    from app.services import agent_service, practice
    course, _ = await access.load_course(db, user, course_id, access.ASSIGNMENT_AUTHORS)
    subject = (await db.execute(select(Subject).where(Subject.id == course.subject_id))).scalar_one_or_none() if course.subject_id else None
    if subject is None:
        raise HTTPException(status_code=422, detail="The course has no subject")
    if body.language not in LANGUAGES or (subject.languages and body.language not in subject.languages):
        raise HTTPException(status_code=422, detail="This subject has no tasks in that language")
    previous = list((await db.execute(select(Task.title).where(Task.subject_id == subject.id, Task.generated_for.is_(None))
                                      .order_by(Task.created_at.desc()).limit(30))).scalars())
    out = []
    try:
        for _ in range(body.count):
            if body.type == "project":
                t = await practice.generate_project(db, user, subject, body.language, body.level, body.topic,
                                                    "en" if lang == "en" else "mk", previous)
            else:
                t = await practice.generate(db, user, subject, body.language, body.level, body.topic,
                                            "en" if lang == "en" else "mk", for_student=False, previous=previous)
            previous = [t.title, *previous]
            out.append({"id": str(t.id), "title": t.title, "language": t.language, "kind": t.kind})
    except agent_service.AIUnavailable:
        raise HTTPException(status_code=503, detail="AI is not configured")
    except HTTPException:
        if not out:
            raise
    return {"tasks": out}


@router.post("/courses/{course_id}/assignments", status_code=201)
async def create_assignment(course_id: uuid.UUID, body: AssignmentIn, db: AsyncSession = Depends(get_db),
                            user: User = Depends(get_current_user)):
    course, role = await access.load_course(db, user, course_id, access.ASSIGNMENT_AUTHORS)
    _lab_limits(role, body)
    a = Assignment(course_id=course_id, title=body.title, created_by=user.id)
    db.add(a)
    await db.flush()
    await _save(db, a, body)
    await _draft_after_save(db, course, a, user, was_published=False, old_due=None)
    await db.commit()
    return await assignment_out(db, a, user, True, datetime.utcnow(), await _groups_map(db, course_id))


@router.get("/assignments/{assignment_id}")
async def assignment_detail(assignment_id: uuid.UUID, request: Request, db: AsyncSession = Depends(get_db),
                            user: User = Depends(get_current_user)):
    a, role = await load_assignment(db, user, assignment_id)
    course = (await db.execute(select(Course).where(Course.id == a.course_id))).scalar_one()
    staff = role in access.COURSE_GRADERS
    out = await assignment_out(db, a, user, staff, datetime.utcnow(), await _groups_map(db, a.course_id), request)
    out.update({"course_name": course.name, "course_code": course.code, "my_role": role,
                "server_time": _iso(datetime.utcnow())})
    if staff:
        out["students_submitted"] = (await db.execute(select(func.count(func.distinct(Submission.user_id))).where(
            Submission.assignment_id == a.id))).scalar_one()
    return out


@router.put("/assignments/{assignment_id}")
async def update_assignment(assignment_id: uuid.UUID, body: AssignmentIn, db: AsyncSession = Depends(get_db),
                            user: User = Depends(get_current_user)):
    a, role = await load_assignment(db, user, assignment_id, staff_only=True, graders=True)
    _lab_limits(role, body)
    was_published, old_due = a.published, a.due_at
    await _save(db, a, body)
    course = (await db.execute(select(Course).where(Course.id == a.course_id))).scalar_one()
    await _draft_after_save(db, course, a, user, was_published, old_due)
    await db.commit()
    return await assignment_out(db, a, user, True, datetime.utcnow(), await _groups_map(db, a.course_id))


@router.delete("/assignments/{assignment_id}", status_code=204)
async def delete_assignment(assignment_id: uuid.UUID, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    a, _ = await load_assignment(db, user, assignment_id, staff_only=True)
    await db.delete(a)
    await db.commit()


# ---------------------------------------------------------------------------
# Exam attempts and signals
# ---------------------------------------------------------------------------

@router.post("/assignments/{assignment_id}/start")
async def start_exam(assignment_id: uuid.UUID, request: Request, db: AsyncSession = Depends(get_db),
                     user: User = Depends(get_current_user)):
    """Start the exam: the personal timer begins now (duration, capped by the deadline)."""
    a, role = await load_assignment(db, user, assignment_id)
    if not a.exam:
        raise HTTPException(status_code=400, detail="This assignment is not an exam")
    if role != "student":
        raise HTTPException(status_code=400, detail="Only students take the exam")
    ip = exam.require_ip(a, request)
    now = datetime.utcnow()
    att = await exam.attempt_of(db, a, user)
    if att is None:
        if a.due_at and now >= a.due_at:
            raise HTTPException(status_code=403, detail="The deadline has passed")
        att = AssignmentAttempt(assignment_id=a.id, user_id=user.id, started_at=now,
                                ends_at=exam.personal_deadline(a, now), ip=ip)
        db.add(att)
        await exam.log_event(db, a, user, "start", ip)
        await db.commit()
    return await assignment_detail(assignment_id, request, db, user)


@router.post("/assignments/{assignment_id}/finish")
async def finish_exam(assignment_id: uuid.UUID, request: Request, db: AsyncSession = Depends(get_db),
                      user: User = Depends(get_current_user)):
    """Hand in early: no more submissions after this."""
    a, _ = await load_assignment(db, user, assignment_id)
    att = await exam.attempt_of(db, a, user)
    if att is None:
        raise HTTPException(status_code=400, detail="Start the exam first")
    if att.finished_at is None:
        att.finished_at = datetime.utcnow()
        await exam.log_event(db, a, user, "finish", exam.client_ip(request))
        await db.commit()
    return await assignment_detail(assignment_id, request, db, user)


@router.post("/assignments/{assignment_id}/events", status_code=204)
async def exam_event(assignment_id: uuid.UUID, body: EventIn, request: Request, db: AsyncSession = Depends(get_db),
                     user: User = Depends(get_current_user)):
    """Signals from the browser during an exam (left the tab / came back / pasted a large block).
    They are shown to the teacher as information — never as proof."""
    a, role = await load_assignment(db, user, assignment_id)
    if role != "student" or not a.exam:
        return
    att = await exam.attempt_of(db, a, user)
    if not exam.attempt_running(att):
        return
    n = (await db.execute(select(func.count()).select_from(ExamEvent).where(
        ExamEvent.assignment_id == a.id, ExamEvent.user_id == user.id))).scalar_one()
    if n >= 1000:  # a script can't flood the log
        return
    await exam.log_event(db, a, user, body.kind, exam.client_ip(request), body.detail, body.task_id)
    await db.commit()


# ---------------------------------------------------------------------------
# Submissions
# ---------------------------------------------------------------------------

@router.post("/assignments/{assignment_id}/tasks/{task_id}/submit")
async def submit(assignment_id: uuid.UUID, task_id: uuid.UUID, body: SubmitIn, request: Request,
                 db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    """Record the submission now (its time is what counts for deadlines and exam timers), then run ALL tests
    (hidden too) in the submission queue. Answers with the result when it is ready within a few seconds,
    otherwise with status "pending" — then the browser asks GET /submissions/{id}/result.
    Points = share of passed tests × task points, minus the late penalty after the deadline."""
    a, role = await load_assignment(db, user, assignment_id)
    staff = role in access.COURSE_GRADERS
    observability.set_context(task_id=task_id)
    at, task, late, now, ip = await _may_hand_in(db, a, user, staff, task_id, request)
    if task.kind != "code":
        raise HTTPException(status_code=400, detail="This task is handed in as a file")
    waiting = (await db.execute(select(func.count()).select_from(Submission).where(
        Submission.user_id == user.id, Submission.status.in_(("pending", "running"))))).scalar_one()
    if waiting >= 2:
        raise HTTPException(status_code=429, detail="Your previous submission is still being tested")

    sub = Submission(assignment_id=a.id, task_id=task_id, user_id=user.id, code=body.code, passed=0, total=0,
                     score=0.0, late=late, submitted_at=now, status="pending")
    up = None
    if body.upload_id:
        up = (await db.execute(select(DiagramUpload).where(DiagramUpload.id == body.upload_id, DiagramUpload.user_id == user.id,
                                                            DiagramUpload.task_id == task_id))).scalar_one_or_none()
        if up is not None:
            sub.file_name, sub.file_type, sub.file_size = up.file_name, up.file_type, len(up.data)
    db.add(sub)
    if up is not None:
        await db.flush()
        db.add(SubmissionFile(submission_id=sub.id, data=up.data))
    if a.exam and not staff:
        await exam.log_event(db, a, user, "submit", ip, "", task_id)
    await db.commit()
    submission_queue.enqueue(sub.id)
    sub = await submission_queue.wait_until_done(sub.id, settings.SUBMIT_WAIT_SECONDS)
    return await submission_result(a, sub, staff, at.points)


async def _may_hand_in(db: AsyncSession, a: Assignment, user: User, staff: bool, task_id, request: Request):
    """Checks shared by code submissions and file uploads: the task is the student's (variant), the assignment is
    open, the network is allowed, the exam is running, the deadline. Returns (assignment task, task, late, now, ip)."""
    rows = await _task_rows(db, a)
    mine = rows if staff else _rows_for_student(rows, a, user.id)
    pair = next(((x, t) for x, t in mine if x.task_id == task_id), None)
    if pair is None:
        raise HTTPException(status_code=404, detail="Task not found")
    at, task = pair
    if task.kind == "offline":
        raise HTTPException(status_code=400, detail="Nothing is handed in for this task")
    now = datetime.utcnow()
    ip = exam.client_ip(request)
    late = False
    if not staff:
        if not access.assignment_open(a, now):
            raise HTTPException(status_code=403, detail="Assignment is not open")
        exam.require_ip(a, request)
        if a.exam:
            att = await exam.attempt_of(db, a, user)
            if att is None:
                raise HTTPException(status_code=403, detail="Start the exam first")
            if not exam.attempt_running(att, now):
                raise HTTPException(status_code=403, detail="Your exam time is over")
        else:
            late = bool(a.due_at and now > a.due_at)
            if late and not a.allow_late:
                raise HTTPException(status_code=403, detail="The deadline has passed")
    return at, task, late, now, ip


# ---------------------------------------------------------------------------
# File work: documents (PDF/Word/pictures) and projects (zip)
# ---------------------------------------------------------------------------

@router.post("/assignments/{assignment_id}/tasks/{task_id}/upload")
async def upload(assignment_id: uuid.UUID, task_id: uuid.UUID, request: Request, file: UploadFile = File(...),
                 db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    """Hand in a file for a document or project task. Every upload is kept; the latest one is graded."""
    a, role = await load_assignment(db, user, assignment_id)
    staff = role in access.COURSE_GRADERS
    at, task, late, now, ip = await _may_hand_in(db, a, user, staff, task_id, request)
    if task.kind not in ("document", "project"):
        raise HTTPException(status_code=400, detail="This task is not handed in as a file")
    data, ctype = await uploads.read_checked(file, task.kind)
    sub = Submission(assignment_id=a.id, task_id=task_id, user_id=user.id, code="", passed=0, total=0, score=0.0,
                     late=late, submitted_at=now, status="done", finished_at=now,
                     file_name=uploads.safe_name(file.filename), file_type=ctype, file_size=len(data))
    db.add(sub)
    await db.flush()
    db.add(SubmissionFile(submission_id=sub.id, data=data))
    if a.exam and not staff:
        await exam.log_event(db, a, user, "submit", ip, sub.file_name, task_id)
    await db.commit()
    return _file_out(sub)


def _file_out(s: Submission) -> dict:
    return {"id": str(s.id), "file_name": s.file_name, "file_type": s.file_type, "file_size": s.file_size,
            "late": s.late, "submitted_at": _iso(s.submitted_at)}


async def _readable_submission(db: AsyncSession, user: User, submission_id) -> tuple[Submission, bytes]:
    """The submission's file, for its author or the course staff."""
    s = (await db.execute(select(Submission).where(Submission.id == submission_id))).scalar_one_or_none()
    if s is None:
        raise HTTPException(status_code=404, detail="Submission not found")
    _, role = await load_assignment(db, user, s.assignment_id)
    if role not in access.COURSE_GRADERS and s.user_id != user.id:
        raise HTTPException(status_code=404, detail="Submission not found")
    data = (await db.execute(select(SubmissionFile.data).where(SubmissionFile.submission_id == s.id))).scalar_one_or_none()
    if data is None:
        raise HTTPException(status_code=404, detail="This submission has no file")
    return s, data


@router.get("/submissions/{submission_id}/download")
async def download(submission_id: uuid.UUID, inline: bool = False, db: AsyncSession = Depends(get_db),
                   user: User = Depends(get_current_user)):
    s, data = await _readable_submission(db, user, submission_id)
    return uploads.file_response(data, s.file_type, s.file_name, inline=inline)


@router.get("/submissions/{submission_id}/tree")
async def project_tree(submission_id: uuid.UUID, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    """The files in a project zip (read only — nothing is extracted or run)."""
    s, data = await _readable_submission(db, user, submission_id)
    if s.file_type != uploads.ZIP:
        raise HTTPException(status_code=400, detail="Not a project")
    return {"files": uploads.zip_tree(data)}


@router.get("/submissions/{submission_id}/entry")
async def project_entry(submission_id: uuid.UUID, path: str = Query(..., max_length=500),
                        db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    """One file of a project zip as text (for reading and line comments)."""
    s, data = await _readable_submission(db, user, submission_id)
    if s.file_type != uploads.ZIP:
        raise HTTPException(status_code=400, detail="Not a project")
    return uploads.zip_entry(data, path)


@router.get("/assignments/{assignment_id}/tasks/{task_id}/uploads")
async def my_uploads(assignment_id: uuid.UUID, task_id: uuid.UUID, db: AsyncSession = Depends(get_db),
                     user: User = Depends(get_current_user)):
    a, _ = await load_assignment(db, user, assignment_id)
    subs = (await db.execute(select(Submission).where(
        Submission.assignment_id == a.id, Submission.task_id == task_id, Submission.user_id == user.id,
        Submission.file_size > 0).order_by(Submission.submitted_at.desc()))).scalars().all()
    return [_file_out(x) for x in subs]


# ---------------------------------------------------------------------------
# Attendance (labs done on site or on another platform)
# ---------------------------------------------------------------------------

@router.put("/assignments/{assignment_id}/attendance")
async def set_attendance(assignment_id: uuid.UUID, body: AttendanceIn, db: AsyncSession = Depends(get_db),
                         user: User = Depends(get_current_user)):
    a, role = await load_assignment(db, user, assignment_id, staff_only=True, graders=True)
    access.require_role(role, access.GRADE_SETTERS, "Not allowed to record attendance")
    if body.status is not None and body.status not in ATTENDANCE:
        raise HTTPException(status_code=422, detail="Unknown attendance status")
    row = (await db.execute(select(Attendance).where(
        Attendance.assignment_id == a.id, Attendance.user_id == body.user_id))).scalar_one_or_none()
    if body.status is None:
        if row is not None:
            await db.delete(row)
    else:
        if row is None:
            row = Attendance(assignment_id=a.id, user_id=body.user_id, status=body.status)
            db.add(row)
        row.status, row.updated_by, row.updated_at = body.status, user.id, datetime.utcnow()
    await db.commit()
    return {"user_id": str(body.user_id), "status": body.status}


async def submission_result(a: Assignment, sub: Submission, staff: bool, points: float) -> dict:
    """What the submitter sees about one submission (respecting the assignment's result visibility)."""
    base = {"submission_id": str(sub.id), "status": sub.status, "submitted_at": _iso(sub.submitted_at),
            "max_points": points, "late": sub.late, "late_penalty": a.late_penalty if sub.late else 0}
    if sub.status in ("pending", "running"):
        return {**base, "queue_position": await submission_queue.position(sub), "visibility": "full" if staff else a.results_visibility,
                "passed": None, "total": None, "score": None, "best_score": None, "results": [], "more_points": False}
    if sub.status == "error":
        return {**base, "visibility": "full" if staff else a.results_visibility, "passed": None, "total": None,
                "score": None, "best_score": None, "results": [], "more_points": False}
    async with AsyncSessionLocal() as db:
        best = (await db.execute(select(func.max(Submission.score)).where(
            Submission.assignment_id == a.id, Submission.task_id == sub.task_id, Submission.user_id == sub.user_id,
            Submission.status == "done"))).scalar_one()
    show_scores = staff or exam.scores_visible(a)
    visibility = "full" if staff else a.results_visibility
    rows = (sub.results or {}).get("staff" if staff else "student", [])
    return {
        **base,
        "visibility": visibility,
        "passed": sub.passed if visibility != "none" else None,
        "total": sub.total,
        "score": sub.score if show_scores else None,
        "best_score": best if show_scores else None,
        "results": rows if visibility == "full" else [],
        # "More points possible": most tests pass — the teacher may look at it (never shown when results are hidden)
        "more_points": visibility != "none" and more_points(a, sub.passed, sub.total),
    }


def more_points(a: Assignment, passed: int, total: int) -> bool:
    return bool(a.review_threshold and total and passed < total and passed * 100 >= a.review_threshold * total)


@router.get("/submissions/{submission_id}/result")
async def get_submission_result(submission_id: uuid.UUID, db: AsyncSession = Depends(get_db),
                                user: User = Depends(get_current_user)):
    """The result of a queued submission (the submitter, or the course staff)."""
    sub = (await db.execute(select(Submission).where(Submission.id == submission_id))).scalar_one_or_none()
    if sub is None:
        raise HTTPException(status_code=404, detail="Submission not found")
    a, role = await load_assignment(db, user, sub.assignment_id)
    staff = role in access.COURSE_GRADERS
    if not staff and sub.user_id != user.id:
        raise HTTPException(status_code=404, detail="Submission not found")
    at = (await db.execute(select(AssignmentTask).where(
        AssignmentTask.assignment_id == a.id, AssignmentTask.task_id == sub.task_id))).scalar_one_or_none()
    await db.commit()
    return await submission_result(a, sub, staff, at.points if at else 0)


@router.get("/assignments/{assignment_id}/submissions")
async def list_submissions(assignment_id: uuid.UUID, task_id: Optional[uuid.UUID] = None,
                           user_id: Optional[uuid.UUID] = None, db: AsyncSession = Depends(get_db),
                           user: User = Depends(get_current_user)):
    """A student's own submissions; staff can look at anyone's (with the submitted code)."""
    a, role = await load_assignment(db, user, assignment_id)
    staff = role in access.COURSE_GRADERS
    who = user_id if (staff and user_id) else user.id
    q = select(Submission).where(Submission.assignment_id == a.id, Submission.user_id == who)
    if task_id:
        q = q.where(Submission.task_id == task_id)
    subs = (await db.execute(q.order_by(Submission.submitted_at.desc()).limit(200))).scalars().all()
    show = staff or exam.scores_visible(a)
    return [{"id": str(s.id), "task_id": str(s.task_id), "status": s.status,
             "passed": s.passed if (staff or a.results_visibility != "none") else None,
             "total": s.total, "score": s.score if show else None,
             "late": s.late, "submitted_at": _iso(s.submitted_at), "code": s.code} for s in subs]


# ---------------------------------------------------------------------------
# Staff: overview, review, grades, comments, publishing
# ---------------------------------------------------------------------------

async def _students(db: AsyncSession, a: Assignment):
    q = select(User, CourseMember.group_id).join(CourseMember, CourseMember.user_id == User.id).where(
        CourseMember.course_id == a.course_id, CourseMember.role == "student")
    if a.group_id:
        q = q.where(CourseMember.group_id == a.group_id)
    return (await db.execute(q.order_by(User.name))).all()


@router.get("/assignments/{assignment_id}/overview")
async def overview(assignment_id: uuid.UUID, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    """Every student of the assignment: their tasks (variant), automatic best, final points, whether graded,
    exam attempt and signals (left tab / pastes)."""
    a, my_role = await load_assignment(db, user, assignment_id, staff_only=True, graders=True)
    rows = await _task_rows(db, a)
    students = await _students(db, a)
    uids = [u.id for u, _ in students]
    best = await exam.best_scores(db, [a.id], uids)
    grades = await exam.grades_map(db, [a.id], uids)
    ratios = await best_ratios(db, a, uids)
    attempts = {str(x.user_id): x for x in (await db.execute(
        select(AssignmentAttempt).where(AssignmentAttempt.assignment_id == a.id))).scalars()}
    signals = {}
    for uid, kind, n in (await db.execute(
            select(ExamEvent.user_id, ExamEvent.kind, func.count()).where(ExamEvent.assignment_id == a.id)
            .group_by(ExamEvent.user_id, ExamEvent.kind))).all():
        signals.setdefault(str(uid), {})[kind] = n
    groups = await _groups_map(db, a.course_id)
    presence = {str(x.user_id): x.status for x in (await db.execute(
        select(Attendance).where(Attendance.assignment_id == a.id))).scalars()}
    out = []
    for u, gid in students:
        tasks, total, to_review = [], None, 0
        for at, t in _rows_for_student(rows, a, u.id):
            key = (str(a.id), str(u.id), str(t.id))
            b, g = best.get(key), grades.get(key)
            final = exam.final_points(b[0] if b else None, g, at.points, auto=t.kind == "code")
            if final is not None:
                total = (total or 0) + final
            submitted = bool(b and b[2])
            # "reviewed": a teacher saved a grade or comment for it (also for offline work, which has no submission)
            reviewed = g is not None
            if submitted and not reviewed:
                to_review += 1
            tasks.append({"task_id": str(t.id), "title": content.t_title(t), "points": at.points, "kind": t.kind,
                          "auto": b[0] if (b and t.kind == "code") else None,
                          "final": final, "submissions": b[2] if b else 0, "late": bool(b[1]) if b else False,
                          "graded": bool(g and (g.adjust or g.override is not None)), "comment": bool(g and g.comment),
                          "reviewed": reviewed,
                          "more_points": g is None and _ratio_flag(a, ratios.get((str(u.id), str(t.id))))})
        att = attempts.get(str(u.id))
        out.append({"user_id": str(u.id), "name": u.name, "email": u.email, "group": groups.get(str(gid)) if gid else None,
                    "tasks": tasks, "total": round(total, 2) if total is not None else None, "to_review": to_review,
                    "attendance": presence.get(str(u.id)),
                    "attempt": None if att is None else {"started_at": _iso(att.started_at), "ends_at": _iso(att.ends_at),
                                                         "finished_at": _iso(att.finished_at), "ip": att.ip},
                    "signals": signals.get(str(u.id), {})})
    return {"my_role": my_role, "assignment_id": str(a.id), "title": a.title, "exam": a.exam, "grades_published": a.grades_published,
            "max_points": exam.max_points([at for at, _ in rows]), "students": out,
            "tasks": [{"task_id": str(t.id), "title": content.t_title(t), "points": at.points, "kind": t.kind,
                       "variant_group": at.variant_group} for at, t in rows]}


@router.get("/assignments/{assignment_id}/review")
async def review(assignment_id: uuid.UUID, user_id: uuid.UUID, task_id: uuid.UUID,
                 db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    """One student's work on one task: all submissions (newest first) with line comments, the grade, signals."""
    a, my_role = await load_assignment(db, user, assignment_id, staff_only=True, graders=True)
    student = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    at_task = (await db.execute(select(AssignmentTask, Task).join(Task, Task.id == AssignmentTask.task_id).where(
        AssignmentTask.assignment_id == a.id, AssignmentTask.task_id == task_id))).first()
    if student is None or at_task is None:
        raise HTTPException(status_code=404, detail="Not found")
    at, task = at_task
    subs = (await db.execute(select(Submission).where(
        Submission.assignment_id == a.id, Submission.user_id == user_id, Submission.task_id == task_id)
        .order_by(Submission.submitted_at.desc()))).scalars().all()
    comments = {}
    if subs:
        for c in (await db.execute(select(CodeComment, User.name).outerjoin(User, User.id == CodeComment.author_id).where(
                CodeComment.submission_id.in_([s.id for s in subs])).order_by(CodeComment.created_at))).all():
            cm, author = c
            comments.setdefault(str(cm.submission_id), []).append(
                {"id": str(cm.id), "line": cm.line, "path": cm.path, "body": cm.body, "author": author,
                 "created_at": _iso(cm.created_at)})
    g = (await exam.grades_map(db, [a.id], [user_id])).get((str(a.id), str(user_id), str(task_id)))
    best = max((s.score for s in subs), default=None) if task.kind == "code" else None
    ref = (await db.execute(select(TaskFile.name, TaskFile.size).where(TaskFile.task_id == task.id))).first()
    events = (await db.execute(select(ExamEvent).where(
        ExamEvent.assignment_id == a.id, ExamEvent.user_id == user_id).order_by(ExamEvent.created_at))).scalars().all()
    return {"my_role": my_role, 
        "student": {"user_id": str(student.id), "name": student.name, "email": student.email},
        "task": {"task_id": str(task.id), "title": content.t_title(task), "language": task.language, "points": at.points,
                 "kind": task.kind, "rubric": task.rubric or [],
                 "reference_file": {"name": ref[0], "size": ref[1]} if ref else None},
        "submissions": [{"id": str(s.id), "passed": s.passed, "total": s.total, "score": s.score, "late": s.late,
                         "submitted_at": _iso(s.submitted_at), "code": s.code, "comments": comments.get(str(s.id), []),
                         "status": s.status, "file_name": s.file_name, "file_type": s.file_type, "file_size": s.file_size}
                        for s in subs],
        "best": best,
        "grade": None if g is None else {"adjust": g.adjust, "override": g.override, "comment": g.comment,
                                         "rubric_scores": g.rubric_scores, "updated_at": _iso(g.updated_at)},
        "final": exam.final_points(best, g, at.points, auto=task.kind == "code"),
        "events": [{"kind": e.kind, "detail": e.detail, "ip": e.ip, "task_id": str(e.task_id) if e.task_id else None,
                    "created_at": _iso(e.created_at)} for e in events],
    }


class AssistIn(BaseModel):
    user_id: uuid.UUID
    task_id: uuid.UUID


@router.post("/assignments/{assignment_id}/grading-assist")
async def grading_assist(assignment_id: uuid.UUID, body: AssistIn, db: AsyncSession = Depends(get_db),
                         user: User = Depends(get_current_user), lang: Optional[str] = Depends(content.use_language)):
    """The grading tutor: suggested points (and rubric scores), what is good, issues by line and a comment for the
    student — for whoever enters the points (a лаборант on labs, assistants, the professor). Nothing is saved."""
    from app.services import agent_service
    a, role = await load_assignment(db, user, assignment_id, staff_only=True, graders=True)
    access.require_role(role, access.GRADE_SETTERS, "Not allowed to set points")
    row = (await db.execute(select(AssignmentTask, Task).join(Task, Task.id == AssignmentTask.task_id).where(
        AssignmentTask.assignment_id == a.id, AssignmentTask.task_id == body.task_id))).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Task not found")
    at, task = row
    subs = (await db.execute(select(Submission).where(
        Submission.assignment_id == a.id, Submission.user_id == body.user_id, Submission.task_id == task.id)
        .order_by(Submission.submitted_at.desc()))).scalars().all()
    if task.kind == "code":
        subs = sorted(subs, key=lambda x: (x.score or 0), reverse=True)   # the best one counts (newest among equals)
    sub = subs[0] if subs else None
    if sub is None:
        raise HTTPException(status_code=404, detail="No submission")
    if not (sub.code or "").strip():
        raise HTTPException(status_code=422, detail="The grading tutor reads code and diagrams, not uploaded files")
    title, description = content.localized(task, lang)
    try:
        out = await agent_service.grading_assist(
            title, description, task.model_solution, task.language, task.rubric or [], at.points,
            sub.score if task.kind == "code" else None, sub.passed, sub.total, sub.code,
            "en" if lang == "en" else "mk")
    except agent_service.AIUnavailable:
        raise HTTPException(status_code=503, detail="AI is not configured")
    except Exception:
        raise HTTPException(status_code=502, detail="The grading tutor could not answer, try again")
    return {**out, "submission_id": str(sub.id), "max_points": at.points}


@router.put("/assignments/{assignment_id}/grades")
async def set_grade(assignment_id: uuid.UUID, body: GradeIn, db: AsyncSession = Depends(get_db),
                    user: User = Depends(get_current_user)):
    a, role = await load_assignment(db, user, assignment_id, staff_only=True, graders=True)
    access.require_role(role, access.GRADE_SETTERS, "Not allowed to set points")
    row = (await db.execute(select(AssignmentTask, Task).join(Task, Task.id == AssignmentTask.task_id).where(
        AssignmentTask.assignment_id == a.id, AssignmentTask.task_id == body.task_id))).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Task not found")
    at, task = row
    if body.rubric_scores is not None:
        # points per criterion, each within its maximum; the task's points = the rubric's share of its total
        crit = {c["id"]: float(c["points"]) for c in (task.rubric or [])}
        if not crit:
            raise HTTPException(status_code=422, detail="This task has no rubric")
        bad = [k for k, v in body.rubric_scores.items() if k not in crit or v < 0 or v > crit[k]]
        if bad:
            raise HTTPException(status_code=422, detail="Rubric points out of range")
        got, of = sum(body.rubric_scores.values()), sum(crit.values())
        body.override = round(at.points * got / of, 2) if of else 0.0
    if body.override is not None and body.override > at.points:
        raise HTTPException(status_code=422, detail="Points above the maximum")
    g = (await exam.grades_map(db, [a.id], [body.user_id])).get((str(a.id), str(body.user_id), str(body.task_id)))
    if g is None:
        g = TaskGrade(assignment_id=a.id, task_id=body.task_id, user_id=body.user_id)
        db.add(g)
    # Only what was sent changes (quick entry sends just the points and must not wipe a comment).
    sent = body.model_fields_set
    if g.adjust is None:
        g.adjust = 0.0
    if "adjust" in sent:
        g.adjust = body.adjust
    if "override" in sent or "rubric_scores" in sent:
        g.override = body.override
    if "comment" in sent:
        g.comment = body.comment.strip()
    if "rubric_scores" in sent:
        g.rubric_scores = body.rubric_scores
    elif "override" in sent:
        g.rubric_scores = None  # points set directly replace a rubric grading
    g.comment = g.comment or ""
    g.graded_by, g.updated_at = user.id, datetime.utcnow()
    await db.commit()
    best = (await db.execute(select(func.max(Submission.score)).where(
        Submission.assignment_id == a.id, Submission.task_id == body.task_id, Submission.user_id == body.user_id))).scalar_one()
    return {"final": exam.final_points(best, g, at.points, auto=task.kind == "code")}


async def _submission_for_staff(db: AsyncSession, user: User, submission_id, comment: bool = False) -> Submission:
    """A submission staff may look at (a лаборант too); `comment`: only the professor and assistants comment."""
    s = (await db.execute(select(Submission).where(Submission.id == submission_id))).scalar_one_or_none()
    if s is None:
        raise HTTPException(status_code=404, detail="Submission not found")
    _, role = await load_assignment(db, user, s.assignment_id, staff_only=True, graders=True)
    if comment:
        access.require_role(role, access.GRADE_SETTERS, "Not allowed to comment")
    return s


@router.post("/submissions/{submission_id}/comments", status_code=201)
async def add_comment(submission_id: uuid.UUID, body: CommentIn, db: AsyncSession = Depends(get_db),
                      user: User = Depends(get_current_user)):
    s = await _submission_for_staff(db, user, submission_id, comment=True)
    c = CodeComment(submission_id=s.id, line=body.line, path=body.path.strip(), body=body.body.strip(), author_id=user.id)
    db.add(c)
    await db.commit()
    return {"id": str(c.id), "line": c.line, "path": c.path, "body": c.body, "author": user.name, "created_at": _iso(c.created_at)}


@router.delete("/comments/{comment_id}", status_code=204)
async def delete_comment(comment_id: uuid.UUID, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    c = (await db.execute(select(CodeComment).where(CodeComment.id == comment_id))).scalar_one_or_none()
    if c is None:
        return
    await _submission_for_staff(db, user, c.submission_id, comment=True)
    await db.delete(c)
    await db.commit()


@router.post("/assignments/{assignment_id}/publish")
async def publish_grades(assignment_id: uuid.UUID, body: PublishIn, background: BackgroundTasks,
                         db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    """Show the final points and the teachers' comments to the students (or hide them again)."""
    a, role = await load_assignment(db, user, assignment_id, staff_only=True, graders=True)
    access.require_role(role, access.GRADE_SETTERS, "Not allowed to publish the points")
    first = body.published and not a.grades_published
    a.grades_published = body.published
    if first:  # drafts only — a teacher reads and sends them from the "Mail" tab
        course = (await db.execute(select(Course).where(Course.id == a.course_id))).scalar_one()
        await emails.draft(db, course, "grades", a, user)
        if standing.category_of(a) in ("k1", "k2", "exam"):
            await emails.draft(db, course, "gradesheet", a, user, audience="staff")
    await db.commit()
    if a.grades_published:  # a course linked to Moodle (LTI) gets the points in its gradebook too
        from app.routers.lti import push_grades_later
        background.add_task(push_grades_later, a.course_id, a.id)
    return {"grades_published": a.grades_published}


@router.get("/assignments/{assignment_id}/feedback")
async def my_feedback(assignment_id: uuid.UUID, task_id: uuid.UUID, db: AsyncSession = Depends(get_db),
                      user: User = Depends(get_current_user)):
    """A student's graded work on one task: the best submission with line comments, points, the comment.
    Only after the teacher published the grades."""
    a, role = await load_assignment(db, user, assignment_id)
    if role != "student":
        raise HTTPException(status_code=400, detail="Only for students")
    if not a.grades_published:
        raise HTTPException(status_code=403, detail="Grades are not published yet")
    pair = next(((x, t) for x, t in _rows_for_student(await _task_rows(db, a), a, user.id) if x.task_id == task_id), None)
    if pair is None:
        raise HTTPException(status_code=404, detail="Task not found")
    at, task = pair
    subs = (await db.execute(select(Submission).where(
        Submission.assignment_id == a.id, Submission.user_id == user.id, Submission.task_id == task_id)
        .order_by(Submission.score.desc(), Submission.submitted_at.desc()))).scalars().all()
    best = subs[0] if subs else None
    # comments on any of the student's submissions, shown with the submission they belong to
    commented = []
    if subs:
        rows = (await db.execute(select(CodeComment).where(CodeComment.submission_id.in_([s.id for s in subs]))
                                 .order_by(CodeComment.line))).scalars().all()
        by_sub = {}
        for c in rows:
            by_sub.setdefault(c.submission_id, []).append({"line": c.line, "path": c.path, "body": c.body})
        if task.kind != "code":
            best = max(subs, key=lambda x: x.submitted_at) if subs else None  # the latest upload is the one graded
        for s in subs:
            if s.id in by_sub or s is best:
                commented.append({"id": str(s.id), "score": s.score, "passed": s.passed, "total": s.total,
                                  "submitted_at": _iso(s.submitted_at), "code": s.code, "best": s is best,
                                  "file_name": s.file_name, "file_type": s.file_type, "file_size": s.file_size,
                                  "comments": by_sub.get(s.id, [])})
    g = (await exam.grades_map(db, [a.id], [user.id])).get((str(a.id), str(user.id), str(task_id)))
    auto = task.kind == "code"
    return {"points": at.points, "kind": task.kind, "auto": best.score if (best and auto) else None,
            "final": exam.final_points(best.score if best else None, g, at.points, auto=auto),
            "adjust": g.adjust if g else 0, "override": g.override if g else None, "comment": g.comment if g else "",
            "rubric": task.rubric or [], "rubric_scores": (g.rubric_scores if g else None),
            "submissions": commented}


# ---------------------------------------------------------------------------
# Similarity (plagiarism check)
# ---------------------------------------------------------------------------

@router.get("/assignments/{assignment_id}/similarity")
async def similar_solutions(assignment_id: uuid.UUID, threshold: float = Query(0.6, ge=0.1, le=1.0),
                            db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    """For each task: pairs of students whose best submissions are structurally similar (renamed variables,
    changed spacing and comments don't hide it). Information for the teacher, not a verdict."""
    a, _ = await load_assignment(db, user, assignment_id, staff_only=True, graders=True)
    rows = await _task_rows(db, a)
    names = {str(u.id): (u.name, u.email) for u, _ in await _students(db, a)}
    out = []
    for at, t in rows:
        if t.kind != "code":
            continue
        subs = (await db.execute(select(Submission).where(
            Submission.assignment_id == a.id, Submission.task_id == t.id)
            .order_by(Submission.user_id, Submission.score.desc(), Submission.submitted_at.desc()))).scalars().all()
        best: dict[str, Submission] = {}
        for s in subs:
            best.setdefault(str(s.user_id), s)
        best = {u: s for u, s in best.items() if u in names}
        if diagrams.is_diagram(t.language):  # diagrams: shared content beyond the model solution + the same layout
            pairs = diagrams.compare_all({u: s.code for u, s in best.items()}, t.language, threshold,
                                         t.model_solution or "", t.starter_code or "")
        else:
            pairs = similarity.compare_all({u: s.code for u, s in best.items()}, t.language, threshold, t.starter_code or "")
        out.append({
            "task_id": str(t.id), "title": content.t_title(t), "language": t.language, "compared": len(best),
            "pairs": [{
                "a": {"user_id": p["a"], "name": names[p["a"]][0], "email": names[p["a"]][1], "submission_id": str(best[p["a"]].id)},
                "b": {"user_id": p["b"], "name": names[p["b"]][0], "email": names[p["b"]][1], "submission_id": str(best[p["b"]].id)},
                "similarity": p["similarity"], "lines_a": p["lines_a"], "lines_b": p["lines_b"],
                "shared": p.get("shared"), "layout": p.get("layout"),
            } for p in pairs],
        })
    return {"threshold": threshold, "tasks": out}


@router.get("/submissions/{submission_id}")
async def submission_code(submission_id: uuid.UUID, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    """Staff: one submission's code (for the side-by-side similarity view)."""
    s = await _submission_for_staff(db, user, submission_id)
    return {"id": str(s.id), "code": s.code, "score": s.score, "passed": s.passed, "total": s.total,
            "submitted_at": _iso(s.submitted_at), "user_id": str(s.user_id), "task_id": str(s.task_id)}


# ---------------------------------------------------------------------------
# Gradebook
# ---------------------------------------------------------------------------

async def gradebook_data(db: AsyncSession, course_id) -> dict:
    groups = await _groups_map(db, course_id)
    assignments = (await db.execute(select(Assignment).where(Assignment.course_id == course_id)
                                    .order_by(Assignment.due_at.is_(None), Assignment.due_at, Assignment.created_at))).scalars().all()
    rows_by_a = {str(a.id): await _task_rows(db, a) for a in assignments}
    a_out = [{"id": str(a.id), "title": a.title, "kind": a.kind, "due_at": _iso(a.due_at),
              "group_id": str(a.group_id) if a.group_id else None, "published": a.published, "exam": a.exam,
              "grades_published": a.grades_published,
              "max_points": exam.max_points([at for at, _ in rows_by_a[str(a.id)]])} for a in assignments]
    students = (await db.execute(
        select(User, CourseMember.group_id).join(CourseMember, CourseMember.user_id == User.id)
        .where(CourseMember.course_id == course_id, CourseMember.role == "student").order_by(User.name)
    )).all()
    uids = [u.id for u, _ in students]
    best = await exam.best_scores(db, [a.id for a in assignments], uids)
    grades = await exam.grades_map(db, [a.id for a in assignments], uids)
    rows = []
    for u, gid in students:
        scores, total = {}, 0.0
        for a in assignments:
            aid = str(a.id)
            applies = a.group_id is None or str(a.group_id) == (str(gid) if gid else None)
            got, late = None, False
            for at, t in _rows_for_student(rows_by_a[aid], a, u.id):
                key = (aid, str(u.id), str(t.id))
                b = best.get(key)
                final = exam.final_points(b[0] if b else None, grades.get(key), at.points, auto=t.kind == "code")
                if final is not None:
                    got = (got or 0) + final
                late = late or bool(b and b[1])
            scores[aid] = {"score": round(got, 2) if got is not None else None, "late": late, "applies": applies}
            total += got or 0
        rows.append({"user_id": str(u.id), "name": u.name, "email": u.email,
                     "group": groups.get(str(gid)) if gid else None, "scores": scores, "total": round(total, 2)})
    return {"assignments": a_out, "students": rows}


@router.get("/courses/{course_id}/gradebook")
async def gradebook(course_id: uuid.UUID, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    await access.load_course(db, user, course_id, access.COURSE_STAFF)
    return await gradebook_data(db, course_id)


@router.get("/courses/{course_id}/gradebook.csv")
async def gradebook_csv(course_id: uuid.UUID, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    course, _ = await access.load_course(db, user, course_id, access.COURSE_STAFF)
    gb = await gradebook_data(db, course_id)
    buf = io.StringIO()
    buf.write("﻿")  # BOM: Excel opens Cyrillic UTF-8 correctly
    w = csv.writer(buf)
    w.writerow(["Name", "E-mail", "Group"] + [f'{a["title"]} (/{a["max_points"]:g})' for a in gb["assignments"]] + ["Total"])
    for s in gb["students"]:
        w.writerow([s["name"], s["email"], s["group"] or ""] +
                   ["" if s["scores"][a["id"]]["score"] is None else s["scores"][a["id"]]["score"] for a in gb["assignments"]] +
                   [s["total"]])
    name = f"{course.code}-gradebook.csv".replace(" ", "_")
    return StreamingResponse(iter([buf.getvalue()]), media_type="text/csv; charset=utf-8",
                             headers={"Content-Disposition": f'attachment; filename="{name}"'})
