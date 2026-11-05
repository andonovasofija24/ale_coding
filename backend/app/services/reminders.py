"""
Deadline reminders, sent automatically (no approval needed): `course.reminder_hours` (24) before the deadline,
only to students who have not handed anything in for that assignment, never twice, and never to students who
turned reminders off in their profile. Exams and on-site-only work get none.

Several backend processes may run this at the same time: the unique (assignment, student) row in reminder_log is
taken with INSERT … ON CONFLICT DO NOTHING, so only one of them sends each reminder.
"""
import asyncio
import logging
from datetime import datetime, timedelta

from sqlalchemy import and_, exists, or_, select
from sqlalchemy.dialects.postgresql import insert

from app.config import settings
from app.database import AsyncSessionLocal
from app.models.comms import Email, ReminderLog
from app.models.course import Assignment, AssignmentTask, Course, CourseMember, Submission
from app.models.task import Task
from app.services import emails, mailer

log = logging.getLogger("ale")
_loop: asyncio.Task | None = None


async def run_once(now: datetime | None = None) -> int:
    """Send the reminders that are due now. Returns how many students got one."""
    now = now or datetime.utcnow()
    total = 0
    async with AsyncSessionLocal() as db:
        rows = (await db.execute(
            select(Assignment, Course).join(Course, Course.id == Assignment.course_id).where(
                Course.reminders_enabled.is_(True), Course.archived.is_(False),
                Assignment.published.is_(True), Assignment.exam.is_(False),
                Assignment.due_at.is_not(None), Assignment.due_at > now,
                or_(Assignment.opens_at.is_(None), Assignment.opens_at <= now),
                # inside the window: due within the next reminder_hours
                Assignment.due_at <= now + Course.reminder_hours * timedelta(hours=1),
                # something to hand in (not only on-site work)
                exists().where(and_(AssignmentTask.assignment_id == Assignment.id, Task.id == AssignmentTask.task_id,
                                    Task.kind != "offline")),
            ))).all()
        for a, course in rows:
            q = select(CourseMember.user_id).where(
                CourseMember.course_id == course.id, CourseMember.role == "student",
                ~exists().where(and_(Submission.assignment_id == a.id, Submission.user_id == CourseMember.user_id)),
                ~exists().where(and_(ReminderLog.assignment_id == a.id, ReminderLog.user_id == CourseMember.user_id)))
            if a.group_id:
                q = q.where(CourseMember.group_id == a.group_id)
            candidates = list((await db.execute(q)).scalars())
            if not candidates:
                continue
            # claim them (only one process wins each student)
            claimed = list((await db.execute(
                insert(ReminderLog).values([{"assignment_id": a.id, "user_id": u, "sent_at": now} for u in candidates])
                .on_conflict_do_nothing(constraint="uq_reminder").returning(ReminderLog.user_id))).scalars())
            if not claimed:
                await db.commit()
                continue
            e = Email(course_id=course.id, assignment_id=a.id, kind="reminder", audience="students", created_by=None,
                      **emails.template("reminder", course, a, ""))
            db.add(e)
            await db.flush()
            n = await emails.queue(db, e, course, user_ids=claimed, reminders=True)
            await db.commit()
            if n:
                mailer.dispatch_later(e.id)
            total += n
    return total


async def _forever() -> None:
    while True:
        try:
            n = await run_once()
            if n:
                log.info("deadline reminders sent: %d", n)
        except Exception:
            log.exception("deadline reminders failed")
        await asyncio.sleep(max(1, settings.REMINDER_CHECK_MINUTES) * 60)


def start() -> None:
    global _loop
    if _loop is None or _loop.done():
        _loop = asyncio.get_running_loop().create_task(_forever())
