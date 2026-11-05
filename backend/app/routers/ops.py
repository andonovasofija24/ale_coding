"""Admin operations: AI provider settings (bring your own key) and the monitoring dashboard."""
from datetime import datetime, timedelta
from typing import Literal, Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, field_validator
from sqlalchemy import select, text, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.deps import get_current_admin
from app.database import get_db
from app.models.ops import AISettings
from app.models.user import User
from app.services import agent_service, ai_config

router = APIRouter(prefix="/admin", tags=["admin-ops"])


# ---------------------------------------------------------------------------
# AI settings — bring your own key
# ---------------------------------------------------------------------------

class AISettingsOut(BaseModel):
    provider: str
    model: str
    base_url: str
    has_key: bool
    key_hint: str
    source: Literal["env", "database"]
    key_unreadable: bool  # saved key can't be decrypted (SECRET_KEY changed)


class AISettingsIn(BaseModel):
    provider: str
    model: str
    base_url: str = ""
    api_key: Optional[str] = None  # empty/None = keep the stored key

    @field_validator("provider")
    @classmethod
    def _provider(cls, v):
        if v not in ai_config.PROVIDERS:
            raise ValueError(f"provider must be one of {', '.join(ai_config.PROVIDERS)}")
        return v

    @field_validator("model")
    @classmethod
    def _model(cls, v):
        v = v.strip()
        if not v or len(v) > 200:
            raise ValueError("model is required")
        return v

    @field_validator("base_url")
    @classmethod
    def _url(cls, v):
        v = v.strip()
        if v and not (v.startswith("http://") or v.startswith("https://")):
            raise ValueError("base_url must start with http:// or https://")
        return v


def _out(cfg: ai_config.AIConfig) -> AISettingsOut:
    return AISettingsOut(
        provider=cfg.provider, model=cfg.model, base_url=cfg.base_url, has_key=bool(cfg.api_key),
        key_hint=cfg.key_hint, source=cfg.source, key_unreadable=ai_config.decrypt_failed(),
    )


def _candidate(body: AISettingsIn) -> ai_config.AIConfig:
    cfg = ai_config.with_overrides(ai_config.platform(), body.provider, body.model, body.base_url, body.api_key)
    if body.provider == "openai_compatible" and not cfg.base_url:
        raise HTTPException(status_code=422, detail="Base URL is required for OpenAI-compatible providers")
    return cfg


@router.get("/ai-settings", response_model=AISettingsOut)
async def get_ai_settings(_: User = Depends(get_current_admin)):
    return _out(ai_config.platform())


@router.post("/ai-settings/test")
async def test_ai_settings(body: AISettingsIn, _: User = Depends(get_current_admin)):
    """Try the given settings (not saved). An empty api_key reuses the stored key for the same provider."""
    return await agent_service.test_connection(_candidate(body))


@router.put("/ai-settings", response_model=AISettingsOut)
async def save_ai_settings(
    body: AISettingsIn, db: AsyncSession = Depends(get_db), admin: User = Depends(get_current_admin),
):
    cfg = _candidate(body)
    if not cfg.api_key:
        raise HTTPException(status_code=422, detail="An API key is required")
    row = (await db.execute(select(AISettings).where(AISettings.id == 1))).scalar_one_or_none()
    if row is None:
        row = AISettings(id=1)
        db.add(row)
    row.provider, row.model, row.base_url = cfg.provider, cfg.model, cfg.base_url
    row.api_key_encrypted = ai_config.encrypt_key(cfg.api_key)
    row.key_hint = ai_config.mask_key(cfg.api_key)
    row.updated_by = admin.id
    row.updated_at = datetime.utcnow()
    await db.commit()
    return _out(await ai_config.load())  # takes effect immediately, no restart


@router.delete("/ai-settings", response_model=AISettingsOut)
async def reset_ai_settings(db: AsyncSession = Depends(get_db), _: User = Depends(get_current_admin)):
    """Forget the saved provider/key and go back to OPENAI_API_KEY from the environment."""
    await db.execute(delete(AISettings).where(AISettings.id == 1))
    await db.commit()
    return _out(await ai_config.load())


# ---------------------------------------------------------------------------
# Monitoring dashboard
# ---------------------------------------------------------------------------

_RANGES = {"24h": (timedelta(hours=24), "hour"), "7d": (timedelta(days=7), "day"), "30d": (timedelta(days=30), "day")}


async def _rows(db: AsyncSession, sql: str, **params) -> list[dict]:
    return [dict(r._mapping) for r in (await db.execute(text(sql), params)).all()]


async def _runner_stats() -> dict | None:
    """Queue state of the code runner (workers, busy, waiting), or None if it can't be reached."""
    try:
        async with httpx.AsyncClient(timeout=3) as c:
            r = await c.get(f"{settings.CODE_RUNNER_URL}/health")
        return r.json() if r.status_code == 200 else None
    except Exception:
        return None


@router.get("/monitoring")
async def monitoring(
    range: Literal["24h", "7d", "30d"] = Query("24h"),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    span, bucket = _RANGES[range]
    now = datetime.utcnow()
    since = now - span
    p = {"since": since}

    ai_where = "kind = 'ai' AND operation <> 'test_connection' AND created_at >= :since"
    ai_totals = (await _rows(db, f"""
        SELECT count(*) AS calls,
               count(*) FILTER (WHERE NOT ok) AS errors,
               coalesce(percentile_cont(0.5) WITHIN GROUP (ORDER BY duration_ms), 0) AS p50_ms,
               coalesce(percentile_cont(0.95) WITHIN GROUP (ORDER BY duration_ms), 0) AS p95_ms,
               coalesce(sum(input_tokens), 0) AS input_tokens,
               coalesce(sum(output_tokens), 0) AS output_tokens
        FROM events WHERE {ai_where}""", **p))[0]

    by_operation = await _rows(db, f"""
        SELECT operation,
               count(*) AS calls,
               count(*) FILTER (WHERE NOT ok) AS errors,
               round(avg(duration_ms)) AS avg_ms,
               percentile_cont(0.95) WITHIN GROUP (ORDER BY duration_ms) AS p95_ms,
               coalesce(sum(input_tokens + output_tokens), 0) AS tokens
        FROM events WHERE {ai_where}
        GROUP BY operation ORDER BY calls DESC""", **p)

    by_model = await _rows(db, f"""
        SELECT provider, model,
               count(*) AS calls,
               count(*) FILTER (WHERE NOT ok) AS errors,
               percentile_cont(0.95) WITHIN GROUP (ORDER BY duration_ms) AS p95_ms,
               coalesce(sum(input_tokens), 0) AS input_tokens,
               coalesce(sum(output_tokens), 0) AS output_tokens
        FROM events WHERE {ai_where}
        GROUP BY provider, model ORDER BY calls DESC""", **p)

    timeline = await _rows(db, f"""
        WITH buckets AS (
            SELECT generate_series(date_trunc('{bucket}', CAST(:since AS timestamp)),
                                   date_trunc('{bucket}', CAST(:now AS timestamp)),
                                   interval '1 {bucket}') AS t
        )
        SELECT b.t AS t,
               count(e.id) FILTER (WHERE e.kind = 'ai' AND e.ok) AS ai_ok,
               count(e.id) FILTER (WHERE e.kind = 'ai' AND NOT e.ok) AS ai_errors,
               count(e.id) FILTER (WHERE e.kind = 'tests') AS test_runs
        FROM buckets b
        LEFT JOIN events e ON date_trunc('{bucket}', e.created_at) = b.t
              AND e.created_at >= :since AND e.operation <> 'test_connection'
        GROUP BY b.t ORDER BY b.t""", since=since, now=now)

    tests_by_lang = await _rows(db, """
        SELECT prog_language AS language,
               count(*) AS runs,
               count(*) FILTER (WHERE NOT ok) AS runner_errors,
               round(avg(duration_ms)) AS avg_ms,
               coalesce(sum((extra->>'passed')::int), 0) AS tests_passed,
               coalesce(sum((extra->>'total')::int), 0) AS tests_total,
               count(*) FILTER (WHERE (extra->>'passed') = (extra->>'total') AND (extra->>'total')::int > 0) AS all_green_runs,
               count(*) FILTER (WHERE coalesce((extra->>'compile_errors')::int, 0) > 0) AS runs_with_compile_errors
        FROM events WHERE kind = 'tests' AND created_at >= :since
        GROUP BY prog_language ORDER BY runs DESC""", **p)

    activity = (await _rows(db, """
        SELECT
          (SELECT count(DISTINCT e.user_id) FROM events e JOIN users u ON u.id = e.user_id
             WHERE e.created_at >= :since AND u.role = 'student') AS active_students,
          (SELECT count(*) FROM sessions WHERE created_at >= :since) AS sessions_started,
          (SELECT count(*) FROM sessions WHERE status = 'completed' AND updated_at >= :since) AS tasks_completed,
          (SELECT count(*) FROM step_attempts WHERE submitted_at >= :since) AS step_checks,
          (SELECT count(*) FROM step_attempts WHERE submitted_at >= :since AND passed) AS steps_passed,
          (SELECT count(*) FROM events WHERE kind = 'limit' AND created_at >= :since) AS rate_limited,
          (SELECT count(DISTINCT user_id) FROM events WHERE kind = 'limit' AND created_at >= :since) AS rate_limited_students
        """, **p))[0]

    recent_errors = await _rows(db, """
        SELECT created_at, kind, operation, provider, model, prog_language, left(error, 400) AS error, request_id
        FROM events WHERE NOT ok AND kind <> 'limit' AND created_at >= :since
        ORDER BY created_at DESC LIMIT 15""", **p)

    cfg = ai_config.platform()
    return {
        "limits": {"ai_per_minute": settings.RATE_AI_PER_MINUTE, "ai_per_day": settings.RATE_AI_PER_DAY,
                   "tests_per_minute": settings.RATE_TESTS_PER_MINUTE},
        "runner": await _runner_stats(),
        "range": range,
        "bucket": bucket,
        "generated_at": now,
        "ai_config": {"provider": cfg.provider, "model": cfg.model, "source": cfg.source, "has_key": bool(cfg.api_key)},
        "ai": ai_totals,
        "ai_by_operation": by_operation,
        "ai_by_model": by_model,
        "timeline": timeline,
        "tests_by_language": tests_by_lang,
        "activity": activity,
        "recent_errors": recent_errors,
    }
