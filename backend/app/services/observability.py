"""
Observability: structured request logs and recorded events (AI calls, test runs).

- Every HTTP request gets a request id (X-Request-ID header, generated if missing) and one JSON log line.
- AI calls, test runs and what people do (activity: sign-ins, sessions, steps, submissions, grades, electives, admin
  changes…) are written to the `events` table with duration, outcome, model and token usage,
  plus who/what they were for (user, task, session). The admin monitoring dashboard reads this table.
- Context (request id, user, task, session) travels in contextvars, so services don't need extra parameters.
- Recording never breaks the request: it uses its own DB session and swallows its own errors.
"""
import contextvars
import json
import logging
import sys
import time
import uuid
from datetime import datetime
from typing import Any, Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.database import AsyncSessionLocal
from app.models.ops import Event

_ctx: contextvars.ContextVar[dict] = contextvars.ContextVar("ale_obs_ctx", default={})

log = logging.getLogger("ale")


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

class _JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        data = {
            "ts": datetime.utcnow().isoformat(timespec="milliseconds") + "Z",
            "level": record.levelname.lower(),
            "logger": record.name,
            "msg": record.getMessage(),
        }
        data.update(getattr(record, "fields", {}) or {})
        rid = _ctx.get().get("request_id")
        if rid and "request_id" not in data:
            data["request_id"] = rid
        if record.exc_info:
            data["exc"] = self.formatException(record.exc_info)
        return json.dumps(data, ensure_ascii=False, default=str)


def setup_logging() -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(_JsonFormatter())
    log.handlers[:] = [handler]
    log.setLevel(logging.INFO)
    log.propagate = False


def log_event(msg: str, level: int = logging.INFO, **fields: Any) -> None:
    log.log(level, msg, extra={"fields": fields})


# ---------------------------------------------------------------------------
# Context
# ---------------------------------------------------------------------------

def set_context(**kwargs: Any) -> None:
    """Add request-scoped context (user_id, task_id, session_id, ...) for events recorded later."""
    _ctx.set({**_ctx.get(), **{k: v for k, v in kwargs.items() if v is not None}})


def context() -> dict:
    return _ctx.get()


class RequestLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        rid = request.headers.get("x-request-id") or uuid.uuid4().hex[:16]
        token = _ctx.set({"request_id": rid})
        start = time.perf_counter()
        status = 500
        try:
            response = await call_next(request)
            status = response.status_code
            response.headers["X-Request-ID"] = rid
            return response
        except Exception:
            log.exception("unhandled error", extra={"fields": {"path": request.url.path}})
            raise
        finally:
            if request.url.path != "/health":
                log_event(
                    "request",
                    logging.WARNING if status >= 500 else logging.INFO,
                    method=request.method,
                    path=request.url.path,
                    status=status,
                    duration_ms=round((time.perf_counter() - start) * 1000),
                )
            _ctx.reset(token)


# ---------------------------------------------------------------------------
# Events
# ---------------------------------------------------------------------------

def _uuid(v: Any) -> Optional[uuid.UUID]:
    try:
        return uuid.UUID(str(v)) if v else None
    except ValueError:
        return None


async def record(
    kind: str,
    operation: str,
    *,
    ok: bool,
    duration_ms: int,
    provider: str = "",
    model: str = "",
    input_tokens: int = 0,
    output_tokens: int = 0,
    prog_language: str = "",
    error: str = "",
    extra: Optional[dict] = None,
) -> None:
    ctx = _ctx.get()
    log_event(
        f"{kind}.{operation}",
        logging.INFO if ok else logging.WARNING,
        ok=ok, duration_ms=duration_ms, model=model, input_tokens=input_tokens, output_tokens=output_tokens,
        **({"error": error[:300]} if error else {}),
    )
    try:
        async with AsyncSessionLocal() as db:
            db.add(Event(
                kind=kind, operation=operation, ok=ok, duration_ms=duration_ms,
                provider=provider, model=model[:200], input_tokens=input_tokens, output_tokens=output_tokens,
                prog_language=prog_language[:16], error=(error or "")[:2000],
                request_id=str(ctx.get("request_id", ""))[:64],
                user_id=_uuid(ctx.get("user_id")), task_id=_uuid(ctx.get("task_id")),
                session_id=_uuid(ctx.get("session_id")), course_id=_uuid(ctx.get("course_id")), extra=extra or {},
            ))
            await db.commit()
    except Exception:  # observability must never break the request
        log.exception("could not record event")


async def activity(operation: str, *, ok: bool = True, error: str = "", **extra: Any) -> None:
    """Something a person did (sign-in, a step checked, a submission, a grade, an elective request…), for the logs.
    The person, task, session and course come from the request context; `extra` holds the details."""
    await record("activity", operation, ok=ok, duration_ms=0, error=error,
                 extra={k: (str(v) if isinstance(v, uuid.UUID) else v) for k, v in extra.items() if v is not None})


async def prune(days: int) -> int:
    """Delete events older than `days` (0 = keep everything). Returns how many went."""
    if days <= 0:
        return 0
    from datetime import timedelta
    from sqlalchemy import delete
    try:
        async with AsyncSessionLocal() as db:
            r = await db.execute(delete(Event).where(Event.created_at < datetime.utcnow() - timedelta(days=days)))
            await db.commit()
            return r.rowcount or 0
    except Exception:
        log.exception("could not prune events")
        return 0
