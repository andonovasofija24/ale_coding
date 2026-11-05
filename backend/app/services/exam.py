"""
Rules that depend on an assignment's settings: AI policy, exam attempts (personal timer), allowed networks,
task variants, and the points a student finally gets (automatic best + staff adjustment / override).
"""
import hashlib
import ipaddress
from datetime import datetime, timedelta

from fastapi import HTTPException, Request
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core import access
from app.models.course import Assignment, AssignmentAttempt, AssignmentTask, ExamEvent, Submission, TaskGrade
from app.models.ops import Event
from app.models.task import Task
from app.models.user import User

STRICTNESS = {"off": 0, "hints": 1, "full": 2}


# ---------------------------------------------------------------------------
# Network
# ---------------------------------------------------------------------------

def client_ip(request: Request) -> str:
    """The student's IP. Behind a reverse proxy set TRUST_PROXY_HEADERS=true to use X-Forwarded-For."""
    if settings.TRUST_PROXY_HEADERS:
        fwd = request.headers.get("x-forwarded-for", "")
        if fwd:
            return fwd.split(",")[0].strip()
    return request.client.host if request.client else ""


def parse_networks(text: str) -> list:
    """'194.149.135.0/24, 10.0.0.5' -> networks. Raises ValueError on a bad entry."""
    nets = []
    for part in text.replace(";", ",").replace("\n", ",").replace(" ", ",").split(","):
        if part.strip():
            nets.append(ipaddress.ip_network(part.strip(), strict=False))
    return nets


def ip_allowed(a: Assignment, ip: str) -> bool:
    if not a.allowed_ips.strip():
        return True
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return False
    return any(addr in n for n in parse_networks(a.allowed_ips))


def require_ip(a: Assignment, request: Request) -> str:
    ip = client_ip(request)
    if not ip_allowed(a, ip):
        raise HTTPException(status_code=403, detail="Not allowed from this network")
    return ip


# ---------------------------------------------------------------------------
# Variants
# ---------------------------------------------------------------------------

def _pick(assignment_id, user_id, group: int, n: int) -> int:
    h = hashlib.sha256(f"{assignment_id}:{user_id}:{group}".encode()).hexdigest()
    return int(h, 16) % n


def tasks_for_student(a_tasks: list[AssignmentTask], assignment_id, user_id) -> list[AssignmentTask]:
    """Tasks without a variant group, plus one task per variant group (the same one every time for this student)."""
    groups: dict[int, list[AssignmentTask]] = {}
    out = []
    for at in a_tasks:
        if at.variant_group is None:
            out.append(at)
        else:
            groups.setdefault(at.variant_group, []).append(at)
    for g, items in groups.items():
        items = sorted(items, key=lambda x: x.order)
        out.append(items[_pick(assignment_id, user_id, g, len(items))])
    return sorted(out, key=lambda x: x.order)


def max_points(a_tasks: list[AssignmentTask]) -> float:
    """Points an assignment is worth: every plain task, plus the most valuable task of each variant group."""
    plain = sum(t.points for t in a_tasks if t.variant_group is None)
    groups: dict[int, float] = {}
    for t in a_tasks:
        if t.variant_group is not None:
            groups[t.variant_group] = max(groups.get(t.variant_group, 0), t.points)
    return plain + sum(groups.values())


# ---------------------------------------------------------------------------
# Exam attempts
# ---------------------------------------------------------------------------

async def attempt_of(db: AsyncSession, a: Assignment, user: User) -> AssignmentAttempt | None:
    return (await db.execute(select(AssignmentAttempt).where(
        AssignmentAttempt.assignment_id == a.id, AssignmentAttempt.user_id == user.id))).scalar_one_or_none()


def personal_deadline(a: Assignment, started_at: datetime) -> datetime | None:
    ends = started_at + timedelta(minutes=a.duration_minutes) if a.duration_minutes else None
    if a.due_at and (ends is None or a.due_at < ends):
        ends = a.due_at
    return ends


def attempt_running(att: AssignmentAttempt | None, now: datetime | None = None) -> bool:
    now = now or datetime.utcnow()
    return att is not None and att.finished_at is None and (att.ends_at is None or now < att.ends_at)


def exam_state(a: Assignment, att: AssignmentAttempt | None, now: datetime | None = None) -> str:
    """not_started | running | over"""
    now = now or datetime.utcnow()
    if att is None:
        return "over" if a.due_at and now >= a.due_at else "not_started"
    return "running" if attempt_running(att, now) else "over"


async def log_event(db: AsyncSession, a: Assignment, user: User, kind: str, ip: str = "", detail: str = "", task_id=None):
    db.add(ExamEvent(assignment_id=a.id, user_id=user.id, kind=kind, ip=ip, detail=detail[:500], task_id=task_id))


# ---------------------------------------------------------------------------
# AI policy
# ---------------------------------------------------------------------------

def _active_clause(now: datetime):
    """The assignment is going on now (published, opened, and before its deadline — or late work is allowed)."""
    return and_(
        Assignment.published.is_(True),
        or_(Assignment.opens_at.is_(None), Assignment.opens_at <= now),
        or_(Assignment.due_at.is_(None), Assignment.due_at > now, Assignment.allow_late.is_(True)),
    )


async def ai_policy(db: AsyncSession, user: User, task: Task) -> dict:
    """How much the AI tutor may help this student with this task right now. The strictest active assignment
    that contains the task decides (so the same task can't be practised with AI elsewhere during an exam)."""
    full = {"mode": "full", "hint_limit": None, "hints_used": 0, "hints_left": None, "assignment_id": None,
            "assignment_title": None, "improve_limit": None, "improve_left": None, "editor_checks": True}
    if access.is_staff(user):
        return full
    now = datetime.utcnow()
    full["editor_checks"] = await editor_checks_allowed(db, user, task, now)
    rows = (await db.execute(
        select(Assignment).join(AssignmentTask, AssignmentTask.assignment_id == Assignment.id).where(
            AssignmentTask.task_id == task.id, Assignment.ai_mode != "full",
            access.visible_to_student_clause(user, now), _active_clause(now),
        )
    )).scalars().all()
    if not rows:
        return full
    a = min(rows, key=lambda x: (STRICTNESS.get(x.ai_mode, 2), x.hint_limit))
    out = {"mode": a.ai_mode, "hint_limit": a.hint_limit if a.ai_mode == "hints" else None, "hints_used": 0,
           "hints_left": None, "assignment_id": str(a.id), "assignment_title": a.title,
           "editor_checks": full["editor_checks"]}
    if a.ai_mode == "hints":
        since = a.opens_at or a.created_at
        used = await _ai_uses(db, user, task, "task_hint", since)
        out["hints_used"] = used
        out["hints_left"] = max(0, a.hint_limit - used)
        improved = await _ai_uses(db, user, task, "task_improve", since)
        out["improve_limit"], out["improve_left"] = a.improve_limit, max(0, a.improve_limit - improved)
    else:
        out["improve_limit"], out["improve_left"] = 0, 0
    return out


async def editor_checks_allowed(db: AsyncSession, user: User, task: Task, now: datetime | None = None) -> bool:
    """False while an active assignment with this task has the editor's compiler checks turned off."""
    if access.is_staff(user):
        return True
    now = now or datetime.utcnow()
    off = (await db.execute(
        select(Assignment.id).join(AssignmentTask, AssignmentTask.assignment_id == Assignment.id).where(
            AssignmentTask.task_id == task.id, Assignment.editor_checks.is_(False),
            access.visible_to_student_clause(user, now), _active_clause(now),
        ).limit(1))).first()
    return off is None


async def _ai_uses(db: AsyncSession, user: User, task: Task, operation: str, since) -> int:
    return (await db.execute(select(func.count()).select_from(Event).where(
        Event.user_id == user.id, Event.task_id == task.id, Event.kind == "ai",
        Event.operation == operation, Event.ok.is_(True), Event.created_at >= since))).scalar_one()


async def require_full_ai(db: AsyncSession, user: User, task: Task) -> None:
    """Step-by-step tutor, step checks, explanations and visualizations need the full AI mode."""
    p = await ai_policy(db, user, task)
    if p["mode"] != "full":
        raise HTTPException(status_code=403, detail="The AI tutor is turned off for this assignment")


# ---------------------------------------------------------------------------
# Points
# ---------------------------------------------------------------------------

def final_points(best: float | None, grade: TaskGrade | None, points: float, auto: bool = True) -> float | None:
    """Automatic best score, then the staff adjustment (kept within 0..points), or the override if set.
    Tasks without automatic tests (`auto=False`: documents, projects, offline work) have points only once graded."""
    if grade is not None and grade.override is not None:
        return round(grade.override, 2)
    if not auto or best is None:
        return None
    adj = grade.adjust if grade else 0.0
    return round(min(max(best + adj, 0.0), points), 2)


async def best_scores(db: AsyncSession, assignment_ids: list, user_ids: list | None = None) -> dict:
    """{(assignment_id, user_id, task_id): (best score, late, submissions)} as strings."""
    if not assignment_ids:
        return {}
    q = select(Submission.assignment_id, Submission.user_id, Submission.task_id,
               func.max(Submission.score), func.bool_or(Submission.late), func.count()).where(
        Submission.assignment_id.in_(assignment_ids)).group_by(
        Submission.assignment_id, Submission.user_id, Submission.task_id)
    if user_ids is not None:
        q = q.where(Submission.user_id.in_(user_ids))
    return {(str(a), str(u), str(t)): (s, late, n) for a, u, t, s, late, n in (await db.execute(q)).all()}


async def grades_map(db: AsyncSession, assignment_ids: list, user_ids: list | None = None) -> dict:
    """{(assignment_id, user_id, task_id): TaskGrade}"""
    if not assignment_ids:
        return {}
    q = select(TaskGrade).where(TaskGrade.assignment_id.in_(assignment_ids))
    if user_ids is not None:
        q = q.where(TaskGrade.user_id.in_(user_ids))
    return {(str(g.assignment_id), str(g.user_id), str(g.task_id)): g for g in (await db.execute(q)).scalars()}


def scores_visible(a: Assignment) -> bool:
    """May a student see their points for this assignment?"""
    return not a.scores_after_publish or a.grades_published
