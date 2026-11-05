"""
Per-student limits, so one student (or a script) can't exhaust the AI budget or the code runner.

- AI requests per minute and test runs per minute: in-memory sliding window (one backend process).
- AI calls per day: counted from the `events` table, so it survives restarts and counts real provider calls.
- One test run at a time per student: a second click while a run is in progress is refused.

Admins are never limited. Every refusal is a 429 with Retry-After and is recorded as a "limit" event,
which the monitoring dashboard counts. Values come from the environment (see config.py).
"""
import asyncio
import logging
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from datetime import datetime, timedelta

from fastapi import Depends, HTTPException
from sqlalchemy import func, select

from app.config import settings
from app.core.deps import get_current_user
from app.database import AsyncSessionLocal
from app.models.ops import Event
from app.models.user import User
from app.services import ai_config, observability

_windows: dict[tuple[str, str], deque] = defaultdict(deque)
_running_tests: set[str] = set()
_lock = asyncio.Lock()


def _refuse(bucket: str, detail: str, retry_after: int):
    asyncio.get_running_loop().create_task(
        observability.record("limit", bucket, ok=False, duration_ms=0, error=detail)
    )
    observability.log_event("rate_limited", logging.WARNING, bucket=bucket)
    raise HTTPException(status_code=429, detail=detail, headers={"Retry-After": str(max(1, retry_after))})


async def _per_minute(user: User, bucket: str, limit: int) -> None:
    if limit <= 0:
        return
    now = time.monotonic()
    async with _lock:
        q = _windows[(bucket, str(user.id))]
        while q and now - q[0] >= 60:
            q.popleft()
        if len(q) >= limit:
            _refuse(bucket, "Too many requests", int(60 - (now - q[0])) + 1)
        q.append(now)


async def allow(user: User, bucket: str, limit: int) -> bool:
    """Like the per-minute limit, but quietly: False instead of a 429 (for background requests such as the
    editor's compiler checks, which simply skip a turn)."""
    if limit <= 0 or user.role == "admin":
        return True
    now = time.monotonic()
    async with _lock:
        q = _windows[(bucket, str(user.id))]
        while q and now - q[0] >= 60:
            q.popleft()
        if len(q) >= limit:
            return False
        q.append(now)
        return True


async def _ai_calls_today(user: User) -> int:
    since = datetime.utcnow() - timedelta(days=1)
    async with AsyncSessionLocal() as db:
        return (await db.execute(
            select(func.count()).select_from(Event).where(
                Event.user_id == user.id, Event.kind == "ai", Event.created_at >= since)
        )).scalar_one()


async def ai_allowed(user: User) -> None:
    """Raise 429 if this student may not make another AI request now."""
    if user.role == "admin":
        return
    await _per_minute(user, "ai", settings.RATE_AI_PER_MINUTE)
    own_key = ai_config.personal() is not None  # on their own key the platform's daily allowance doesn't apply
    if not own_key and settings.RATE_AI_PER_DAY > 0 and await _ai_calls_today(user) >= settings.RATE_AI_PER_DAY:
        _refuse("ai_day", "Daily AI limit reached", 3600)


async def limit_ai(user: User = Depends(get_current_user)) -> User:
    """Dependency for endpoints that call the AI."""
    await ai_allowed(user)
    return user


@asynccontextmanager
async def test_run(user: User):
    """Rate limit + one run at a time per student, held for the duration of the run."""
    if user.role == "admin":
        yield
        return
    await _per_minute(user, "tests", settings.RATE_TESTS_PER_MINUTE)
    key = str(user.id)
    async with _lock:
        if key in _running_tests:
            _refuse("tests_parallel", "A test run is already in progress", 3)
        _running_tests.add(key)
    try:
        yield
    finally:
        _running_tests.discard(key)


def reset() -> None:
    """For tests."""
    _windows.clear()
    _running_tests.clear()
