"""
A person's own AI key ("bring your own key" for one user — students too).

  GET    /me/ai-key          what is saved (provider, model, a hint of the key — never the key itself)
  POST   /me/ai-key/test     try a provider + key (not saved)
  PUT    /me/ai-key          save it: from now on the person's AI help runs on it (the platform's daily AI
                             allowance no longer applies to them; the per-minute limit still does)
  DELETE /me/ai-key          forget it: back to the platform's key
  POST   /me/ai-key/reveal   the saved key in full, for its owner only (the "eye" in the profile)
  POST   /admin/ai-settings/reveal   the platform key in full, for the admin (the "eye" in the AI settings)

Revealing is recorded (who, when) — never the key.
"""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_admin, get_current_user
from app.database import get_db
from app.models.user import User, UserAIKey
from app.services import agent_service, ai_config, observability

router = APIRouter(tags=["ai-keys"])


class OwnKeyIn(BaseModel):
    provider: str
    model: str = ""
    base_url: str = ""
    api_key: Optional[str] = None  # empty = keep the saved key (same provider)

    @field_validator("provider")
    @classmethod
    def _provider(cls, v):
        if v not in ai_config.PROVIDERS:
            raise ValueError(f"provider must be one of {', '.join(ai_config.PROVIDERS)}")
        return v

    @field_validator("model", "base_url")
    @classmethod
    def _strip(cls, v):
        v = (v or "").strip()
        if len(v) > 300:
            raise ValueError("too long")
        return v

    @field_validator("base_url")
    @classmethod
    def _url(cls, v):
        if v and not (v.startswith("http://") or v.startswith("https://")):
            raise ValueError("base_url must start with http:// or https://")
        return v


class OwnKeyOut(BaseModel):
    has_key: bool
    provider: str = ""
    model: str = ""
    base_url: str = ""
    key_hint: str = ""
    key_unreadable: bool = False  # saved, but can't be decrypted any more (the server's secret changed)
    default_models: dict = ai_config.DEFAULT_MODELS


async def _row(db: AsyncSession, user: User) -> UserAIKey | None:
    return (await db.execute(select(UserAIKey).where(UserAIKey.user_id == user.id))).scalar_one_or_none()


def _out(row: UserAIKey | None) -> OwnKeyOut:
    if row is None:
        return OwnKeyOut(has_key=False)
    return OwnKeyOut(has_key=True, provider=row.provider, model=row.model, base_url=row.base_url, key_hint=row.key_hint,
                     key_unreadable=not ai_config.decrypt_key(row.api_key_encrypted))


def _candidate(body: OwnKeyIn, row: UserAIKey | None) -> ai_config.AIConfig:
    key = body.api_key or ""
    if not key and row is not None and row.provider == body.provider:
        key = ai_config.decrypt_key(row.api_key_encrypted) or ""
    if not key:
        raise HTTPException(status_code=422, detail="An API key is required")
    if body.provider == "openai_compatible" and not body.base_url:
        raise HTTPException(status_code=422, detail="Base URL is required for OpenAI-compatible providers")
    model = body.model or ai_config.DEFAULT_MODELS.get(body.provider, "")
    if not model:
        raise HTTPException(status_code=422, detail="Write the model name")
    return ai_config.AIConfig(provider=body.provider, model=model, api_key=key.strip(), base_url=body.base_url, source="personal")


@router.get("/me/ai-key", response_model=OwnKeyOut)
async def get_own_key(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    return _out(await _row(db, user))


@router.post("/me/ai-key/test")
async def test_own_key(body: OwnKeyIn, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    cfg = _candidate(body, await _row(db, user))
    await db.commit()
    return await agent_service.test_connection(cfg)


@router.put("/me/ai-key", response_model=OwnKeyOut)
async def save_own_key(body: OwnKeyIn, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    row = await _row(db, user)
    cfg = _candidate(body, row)
    if row is None:
        row = UserAIKey(user_id=user.id)
        db.add(row)
    row.provider, row.model, row.base_url = cfg.provider, cfg.model, cfg.base_url
    row.api_key_encrypted = ai_config.encrypt_key(cfg.api_key)
    row.key_hint = ai_config.mask_key(cfg.api_key)
    row.updated_at = datetime.utcnow()
    await db.commit()
    ai_config.use_personal(cfg)
    return _out(row)


@router.delete("/me/ai-key", response_model=OwnKeyOut)
async def delete_own_key(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    await db.execute(delete(UserAIKey).where(UserAIKey.user_id == user.id))
    await db.commit()
    ai_config.use_personal(None)
    return OwnKeyOut(has_key=False)


@router.post("/me/ai-key/reveal")
async def reveal_own_key(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    row = await _row(db, user)
    key = ai_config.decrypt_key(row.api_key_encrypted) if row else ""
    if not key:
        raise HTTPException(status_code=404, detail="No saved key")
    await observability.record("audit", "reveal_own_ai_key", ok=True, duration_ms=0)
    return {"api_key": key}


@router.post("/admin/ai-settings/reveal")
async def reveal_platform_key(_: User = Depends(get_current_admin)):
    key = ai_config.platform().api_key
    if not key:
        raise HTTPException(status_code=404, detail="No saved key")
    await observability.record("audit", "reveal_platform_ai_key", ok=True, duration_ms=0)
    return {"api_key": key}
