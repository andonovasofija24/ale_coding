"""
Logs: everything the platform records in `events` — AI calls (steps, hints, visualisation, explanations, the
grading tutor, task generation…), test runs, and what people do (activity: sign-ins, sessions, steps checked,
submissions, grades, comments, electives, admin changes, LTI launches), plus rate limits and audits.

  GET /admin/logs            admin: all of it, with filters and paging (newest first; ?before=<id> for more)
  GET /admin/logs.csv        admin: the same as a CSV file (up to 20 000 rows)
  GET /courses/{id}/logs     the professor / assistants: what happened in the course, and the course's students'
                             own practice in its subject
  GET /me/activity           a person's own activity (no model / token / request details)

Old events are deleted at start-up after LOG_RETENTION_DAYS (default 180; 0 keeps everything).
"""
import csv
import io
import uuid
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import access
from app.core.deps import get_current_admin, get_current_user
from app.database import get_db
from app.models.course import Course, CourseMember
from app.models.ops import Event
from app.models.task import Task
from app.models.user import User

router = APIRouter(tags=["logs"])

KINDS = ("ai", "tests", "activity", "limit", "audit")
SPANS = {"1h": timedelta(hours=1), "24h": timedelta(hours=24), "7d": timedelta(days=7), "30d": timedelta(days=30)}


def _filters(q, *, kind: Optional[str], operation: Optional[str], ok: Optional[bool], span: Optional[str],
             since: Optional[datetime], until: Optional[datetime], user_id, course_id, task_id, search: str):
    if kind == "errors":
        q = q.where(Event.ok.is_(False))
    elif kind:
        q = q.where(Event.kind.in_([k for k in kind.split(",") if k in KINDS]))
    if operation:
        q = q.where(Event.operation == operation)
    if ok is not None:
        q = q.where(Event.ok.is_(ok))
    if span in SPANS:
        q = q.where(Event.created_at >= datetime.utcnow() - SPANS[span])
    if since:
        q = q.where(Event.created_at >= since.replace(tzinfo=None))
    if until:
        q = q.where(Event.created_at <= until.replace(tzinfo=None))
    if user_id:
        q = q.where(Event.user_id == user_id)
    if course_id:
        q = q.where(Event.course_id == course_id)
    if task_id:
        q = q.where(Event.task_id == task_id)
    if search.strip():
        like = f"%{search.strip().lower()}%"
        q = q.where(or_(func.lower(User.name).like(like), func.lower(User.email).like(like),
                        func.lower(Task.title).like(like), func.lower(Event.operation).like(like),
                        func.lower(Event.error).like(like)))
    return q


def _base():
    return (select(Event, User, Task, Course)
            .outerjoin(User, User.id == Event.user_id)
            .outerjoin(Task, Task.id == Event.task_id)
            .outerjoin(Course, Course.id == Event.course_id))


def _iso(d: Optional[datetime]) -> Optional[str]:
    return d.isoformat() + "Z" if d else None


def _row(e: Event, u: Optional[User], t: Optional[Task], c: Optional[Course], full: bool) -> dict:
    out = {"id": e.id, "at": _iso(e.created_at), "kind": e.kind, "operation": e.operation, "ok": e.ok,
           "duration_ms": e.duration_ms, "language": e.prog_language or None,
           "user": {"id": str(u.id), "name": u.name, "email": u.email, "role": u.role} if u else None,
           "task": {"id": str(t.id), "title": t.title} if t else None,
           "course": {"id": str(c.id), "code": c.code, "name": c.name} if c else None,
           "session_id": str(e.session_id) if e.session_id else None,
           "extra": e.extra or {}, "error": (e.error or "")[:500] if full else ((e.error or "")[:160] or None)}
    if full:
        out.update({"provider": e.provider or None, "model": e.model or None, "input_tokens": e.input_tokens,
                    "output_tokens": e.output_tokens, "request_id": e.request_id or None})
    return out


PEOPLE = ("student", "member")   # details that name another person by id: shown with their name


async def _page(db: AsyncSession, q, before: Optional[int], limit: int, full: bool, roles: Optional[dict] = None) -> dict:
    if before:
        q = q.where(Event.id < before)
    rows = (await db.execute(q.order_by(Event.id.desc()).limit(limit + 1))).all()
    more = len(rows) > limit
    rows = rows[:limit]
    items = [_row(*r, full=full) for r in rows]
    ids = {x["extra"][k] for x in items for k in PEOPLE if isinstance(x["extra"].get(k), str)}
    names = {}
    if ids:
        valid = []
        for i in ids:
            try:
                valid.append(uuid.UUID(i))
            except ValueError:
                pass
        names = {str(u.id): u.name for u in (await db.execute(select(User).where(User.id.in_(valid)))).scalars()}
    for x in items:
        for k in PEOPLE:
            if x["extra"].get(k) in names:
                x["about"] = names[x["extra"][k]]
        if roles is not None and x.get("user"):
            x["user"]["course_role"] = roles.get(x["user"]["id"])   # the role in this course
    return {"items": items, "next_before": rows[-1][0].id if more and rows else None}


@router.get("/admin/logs")
async def admin_logs(kind: Optional[str] = None, operation: Optional[str] = None, ok: Optional[bool] = None,
                     span: Optional[str] = "24h", since: Optional[datetime] = None, until: Optional[datetime] = None,
                     user_id: Optional[uuid.UUID] = None, course_id: Optional[uuid.UUID] = None,
                     task_id: Optional[uuid.UUID] = None, q: str = "", before: Optional[int] = None,
                     limit: int = Query(100, ge=1, le=500), db: AsyncSession = Depends(get_db),
                     _: User = Depends(get_current_admin)):
    query = _filters(_base(), kind=kind, operation=operation, ok=ok, span=span, since=since, until=until,
                     user_id=user_id, course_id=course_id, task_id=task_id, search=q)
    out = await _page(db, query, before, limit, full=True)
    # what can be filtered by, and the counts of the chosen period (without the kind / operation filters)
    counted = _filters(select(Event.kind, Event.operation, Event.ok, func.count()).select_from(Event)
                       .outerjoin(User, User.id == Event.user_id).outerjoin(Task, Task.id == Event.task_id),
                       kind=None, operation=None, ok=None, span=span, since=since, until=until, user_id=user_id,
                       course_id=course_id, task_id=task_id, search=q).group_by(Event.kind, Event.operation, Event.ok)
    ops: dict = {}
    totals = {k: 0 for k in KINDS} | {"errors": 0, "all": 0}
    for k, op, good, n in (await db.execute(counted)).all():
        ops.setdefault(op, {"operation": op, "kind": k, "count": 0, "errors": 0})
        ops[op]["count"] += n
        totals[k] = totals.get(k, 0) + n
        totals["all"] += n
        if not good:
            ops[op]["errors"] += n
            totals["errors"] += n
    out["operations"] = sorted(ops.values(), key=lambda x: -x["count"])
    out["totals"] = totals
    return out


@router.get("/admin/logs.csv")
async def admin_logs_csv(kind: Optional[str] = None, operation: Optional[str] = None, ok: Optional[bool] = None,
                         span: Optional[str] = "24h", since: Optional[datetime] = None, until: Optional[datetime] = None,
                         user_id: Optional[uuid.UUID] = None, course_id: Optional[uuid.UUID] = None,
                         task_id: Optional[uuid.UUID] = None, q: str = "", db: AsyncSession = Depends(get_db),
                         _: User = Depends(get_current_admin)):
    query = _filters(_base(), kind=kind, operation=operation, ok=ok, span=span, since=since, until=until,
                     user_id=user_id, course_id=course_id, task_id=task_id, search=q)
    rows = (await db.execute(query.order_by(Event.id.desc()).limit(20_000))).all()
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["id", "time (UTC)", "kind", "operation", "ok", "duration ms", "user", "email", "role", "course",
                "task", "language", "model", "input tokens", "output tokens", "details", "error", "request id"])
    for e, u, t, c in rows:
        details = "; ".join(f"{k}={v}" for k, v in (e.extra or {}).items())
        w.writerow([e.id, e.created_at.isoformat(timespec="seconds"), e.kind, e.operation, "yes" if e.ok else "no",
                    e.duration_ms, u.name if u else "", u.email if u else "", u.role if u else "", c.code if c else "",
                    t.title if t else "", e.prog_language, e.model, e.input_tokens, e.output_tokens, details,
                    (e.error or "")[:500], e.request_id])
    name = f"ale-logs-{datetime.utcnow():%Y%m%d-%H%M}.csv"
    return Response("﻿" + buf.getvalue(), media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="{name}"'})


@router.get("/courses/{course_id}/logs")
async def course_logs(course_id: uuid.UUID, kind: Optional[str] = None, operation: Optional[str] = None,
                      ok: Optional[bool] = None, span: Optional[str] = "7d", user_id: Optional[uuid.UUID] = None,
                      q: str = "", before: Optional[int] = None, limit: int = Query(100, ge=1, le=300),
                      db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    """What happened in the course (assignments, submissions, grades, its AI calls and test runs), and its
    students' own practice in the course's subject — for the professor and the assistants."""
    course, _ = await access.load_course(db, user, course_id, "activity.view")
    students = select(CourseMember.user_id).where(CourseMember.course_id == course.id)
    scope = Event.course_id == course.id
    if course.subject_id:
        practice = and_(Event.course_id.is_(None), Event.user_id.in_(students), Task.subject_id == course.subject_id)
        scope = or_(scope, practice)
    query = _filters(_base().where(scope), kind=kind if kind != "audit" else None, operation=operation, ok=ok,
                     span=span, since=None, until=None, user_id=user_id, course_id=None, task_id=None, search=q)
    query = query.where(Event.kind.in_(["ai", "tests", "activity", "limit"]))
    roles = {str(uid): r for uid, r in (await db.execute(select(CourseMember.user_id, CourseMember.role).where(
        CourseMember.course_id == course.id))).all()}
    return await _page(db, query, before, limit, full=False, roles=roles)


@router.get("/me/activity")
async def my_activity(span: Optional[str] = "30d", kind: Optional[str] = None, before: Optional[int] = None,
                      limit: int = Query(50, ge=1, le=200), db: AsyncSession = Depends(get_db),
                      user: User = Depends(get_current_user)):
    query = _filters(_base().where(Event.user_id == user.id, Event.kind.in_(["ai", "tests", "activity", "limit"])),
                     kind=kind if kind != "audit" else None, operation=None, ok=None, span=span, since=None,
                     until=None, user_id=None, course_id=None, task_id=None, search="")
    out = await _page(db, query, before, limit, full=False)
    for x in out["items"]:
        x.pop("user", None)
    return out
