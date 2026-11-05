"""
The submission queue.

"Submit" stores the submission at once (status "pending", receipt time = submission time, so a busy runner can
never make a student miss an exam deadline) and the tests run here, in the background, at most
SUBMISSION_WORKERS at a time — oldest first. The browser asks for the result until it is ready.

Nothing holds a database connection while tests run. Every step that changes a submission is a single
conditional UPDATE, so several backend processes can share the queue without testing anything twice:
  pending --(claim: UPDATE … WHERE status='pending')--> running --> done | error
A sweeper re-queues submissions left "running" by a crashed or restarted backend, and picks up "pending" ones
that no process is handling (e.g. received just before a restart).
"""
import asyncio
import logging
import time
from datetime import datetime, timedelta

from sqlalchemy import func, select, update

from app.config import settings
from app.database import AsyncSessionLocal
from app.models.course import Assignment, AssignmentTask, Submission
from app.models.task import Task, TestCase
from app.services import code_runner_client, grading

log = logging.getLogger("ale")

MAX_ATTEMPTS = 3
STUCK_AFTER = timedelta(minutes=10)

_slots: asyncio.Semaphore | None = None
_inflight: set[str] = set()
_sweeper: asyncio.Task | None = None


def _semaphore() -> asyncio.Semaphore:
    global _slots
    if _slots is None:
        _slots = asyncio.Semaphore(max(1, settings.SUBMISSION_WORKERS))
    return _slots


def enqueue(submission_id) -> None:
    """Test this submission as soon as a slot is free (FIFO). Safe to call more than once."""
    _ensure_sweeper()
    sid = str(submission_id)
    if sid in _inflight:
        return
    _inflight.add(sid)
    asyncio.get_running_loop().create_task(_process(sid))


async def position(submission: Submission) -> int:
    """How many submissions are ahead of this one (0 = it is being tested)."""
    if submission.status != "pending":
        return 0
    async with AsyncSessionLocal() as db:
        return (await db.execute(select(func.count()).select_from(Submission).where(
            Submission.status.in_(("pending", "running")), Submission.submitted_at < submission.submitted_at))).scalar_one()


async def wait_until_done(submission_id, seconds: float) -> Submission:
    """Poll until the submission is tested or `seconds` pass; returns its latest state."""
    end = time.monotonic() + seconds
    delay = 0.2
    while True:
        async with AsyncSessionLocal() as db:
            sub = (await db.execute(select(Submission).where(Submission.id == submission_id))).scalar_one()
        if sub.status in ("done", "error") or time.monotonic() >= end:
            return sub
        await asyncio.sleep(delay)
        delay = min(delay * 1.5, 1.0)


async def _process(sid: str) -> None:
    try:
        async with _semaphore():
            if not await _claim(sid):
                return
            await _grade(sid)
    except Exception:  # never let a background task die silently
        log.exception("submission %s: unexpected error in the queue", sid)
    finally:
        _inflight.discard(sid)


async def _claim(sid: str) -> bool:
    async with AsyncSessionLocal() as db:
        res = await db.execute(update(Submission).where(Submission.id == sid, Submission.status == "pending")
                               .values(status="running", started_at=datetime.utcnow(), attempts=Submission.attempts + 1)
                               .returning(Submission.id))
        claimed = res.first() is not None
        await db.commit()
    return claimed


async def _grade(sid: str) -> None:
    async with AsyncSessionLocal() as db:
        sub = (await db.execute(select(Submission).where(Submission.id == sid))).scalar_one()
        a = (await db.execute(select(Assignment).where(Assignment.id == sub.assignment_id))).scalar_one()
        at = (await db.execute(select(AssignmentTask).where(
            AssignmentTask.assignment_id == a.id, AssignmentTask.task_id == sub.task_id))).scalar_one_or_none()
        task = (await db.execute(select(Task).where(Task.id == sub.task_id))).scalar_one()
        test_cases = (await db.execute(select(TestCase).where(TestCase.task_id == task.id)
                                       .order_by(TestCase.order))).scalars().all()
        code, late, attempts = sub.code, sub.late, sub.attempts
        points = at.points if at else 0.0
        penalty = a.late_penalty
    # the connection is back in the pool from here on — the tests may take a while

    try:
        if not test_cases:
            raise ValueError("No test cases found for this task")
        results = await code_runner_client.run_tests(code, grading.test_payload(test_cases), task.language,
                                                     task.model_solution or "", task.content_lang or "mk")
    except Exception as e:
        retry = attempts < MAX_ATTEMPTS and not isinstance(e, ValueError)
        log.warning("submission %s: attempt %d failed: %s", sid, attempts, e)
        async with AsyncSessionLocal() as db:
            await db.execute(update(Submission).where(Submission.id == sid).values(
                status="pending" if retry else "error", error=f"{type(e).__name__}: {e}"[:2000],
                finished_at=None if retry else datetime.utcnow()))
            await db.commit()
        if retry:
            await asyncio.sleep(5 * attempts)
            _inflight.discard(sid)
            enqueue(sid)
        return

    passed, total = sum(1 for r in results if r.passed), len(results)
    score = points * passed / total if total else 0.0
    if late:
        score *= (100 - penalty) / 100
    rows = {
        "staff": [r.model_dump() for r in grading.result_rows(test_cases, results, reveal_hidden=True)],
        "student": [r.model_dump() for r in grading.result_rows(test_cases, results, reveal_hidden=False)],
    }
    async with AsyncSessionLocal() as db:
        await db.execute(update(Submission).where(Submission.id == sid).values(
            status="done", passed=passed, total=total, score=round(score, 2), results=rows, error="",
            finished_at=datetime.utcnow()))
        await db.commit()


# ---------------------------------------------------------------------------
# Sweeper: recover after restarts
# ---------------------------------------------------------------------------

def _ensure_sweeper() -> None:
    global _sweeper
    if _sweeper is None or _sweeper.done():
        _sweeper = asyncio.get_running_loop().create_task(_sweep_forever())


async def _sweep_forever() -> None:
    while True:
        try:
            await sweep()
        except Exception:
            log.exception("submission queue sweep failed")
        await asyncio.sleep(15)


async def sweep() -> None:
    now = datetime.utcnow()
    async with AsyncSessionLocal() as db:
        await db.execute(update(Submission).where(Submission.status == "running", Submission.started_at < now - STUCK_AFTER)
                         .values(status="pending"))
        await db.commit()
        waiting = (await db.execute(select(Submission.id).where(
            Submission.status == "pending", Submission.submitted_at < now - timedelta(seconds=10))
            .order_by(Submission.submitted_at).limit(500))).scalars().all()
    for sid in waiting:
        if str(sid) not in _inflight:
            enqueue(sid)


def start() -> None:
    """Called at startup: pick up whatever an earlier run of the backend left in the queue."""
    _ensure_sweeper()
