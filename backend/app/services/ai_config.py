"""
Which AI provider / model / API key the platform uses ("bring your own key").

- The admin sets provider, model, optional base URL and the API key in the admin UI.
- The key is encrypted at rest with Fernet; the encryption key is derived from SECRET_KEY.
  (If SECRET_KEY changes, the stored key can no longer be decrypted — the admin simply enters it again.)
- The key never leaves the server: the API only returns a short hint such as "sk-…a1b2".
- Without saved settings the platform uses OPENAI_API_KEY from the environment and gpt-4o (previous behaviour).
- The active configuration is cached in memory and replaced when the admin saves, so no restart is needed.
"""
import base64
import hashlib
from contextvars import ContextVar
from dataclasses import dataclass, replace
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import select

from app.config import settings
from app.database import AsyncSessionLocal
from app.models.ops import AISettings

PROVIDERS = ("openai", "anthropic", "openai_compatible")
DEFAULT_MODELS = {"openai": "gpt-4o", "anthropic": "claude-sonnet-5-5", "openai_compatible": ""}


@dataclass(frozen=True)
class AIConfig:
    provider: str
    model: str
    api_key: str
    base_url: str = ""
    source: str = "env"  # "env" | "database" | "personal" (a user's own key)

    @property
    def key_hint(self) -> str:
        return mask_key(self.api_key)


def mask_key(key: str) -> str:
    if not key:
        return ""
    return f"{key[:3]}…{key[-4:]}" if len(key) > 10 else "…"


def _fernet() -> Fernet:
    digest = hashlib.sha256(("ale-ai-key:" + settings.SECRET_KEY).encode()).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_key(key: str) -> str:
    return _fernet().encrypt(key.encode()).decode() if key else ""


def decrypt_key(token: str) -> Optional[str]:
    if not token:
        return ""
    try:
        return _fernet().decrypt(token.encode()).decode()
    except (InvalidToken, ValueError):
        return None  # SECRET_KEY changed since the key was saved


def env_config() -> AIConfig:
    return AIConfig(provider="openai", model="gpt-4o", api_key=settings.OPENAI_API_KEY, source="env")


_current: AIConfig = env_config()
_decrypt_failed = False
# The signed-in person's own provider + key (set per request by get_current_user), or None.
_personal: ContextVar[Optional[AIConfig]] = ContextVar("ale_personal_ai", default=None)


def current() -> AIConfig:
    """The configuration AI calls use now: the person's own key if they saved one, else the platform's."""
    return _personal.get() or _current


def platform() -> AIConfig:
    """The platform's configuration (what the admin set), whoever is signed in."""
    return _current


def personal() -> Optional[AIConfig]:
    return _personal.get()


def use_personal(cfg: Optional[AIConfig]) -> None:
    _personal.set(cfg)


def personal_from_row(row) -> Optional[AIConfig]:
    """A UserAIKey row -> config (None if it can't be decrypted any more, e.g. SECRET_KEY changed)."""
    if row is None:
        return None
    key = decrypt_key(row.api_key_encrypted)
    if not key:
        return None
    return AIConfig(provider=row.provider, model=row.model or DEFAULT_MODELS.get(row.provider, ""), api_key=key,
                    base_url=row.base_url or "", source="personal")


def decrypt_failed() -> bool:
    return _decrypt_failed


def _from_row(row: AISettings) -> AIConfig:
    global _decrypt_failed
    key = decrypt_key(row.api_key_encrypted)
    _decrypt_failed = key is None
    return AIConfig(provider=row.provider, model=row.model, api_key=key or "", base_url=row.base_url or "", source="database")


async def load() -> AIConfig:
    """(Re)load the active configuration from the database; called on startup and after saving."""
    global _current, _decrypt_failed
    async with AsyncSessionLocal() as db:
        row = (await db.execute(select(AISettings).where(AISettings.id == 1))).scalar_one_or_none()
    if row is None:
        _decrypt_failed = False
        _current = env_config()
    else:
        _current = _from_row(row)
    return _current


def with_overrides(base: AIConfig, provider: str, model: str, base_url: str, api_key: Optional[str]) -> AIConfig:
    """Config for testing/saving: an empty api_key means "keep the stored one" (only if the provider is unchanged)."""
    key = api_key if api_key else (base.api_key if provider == base.provider else "")
    return replace(base, provider=provider, model=model.strip(), base_url=base_url.strip(), api_key=key)


def build_model(cfg: AIConfig):
    """Create the Strands model object for a configuration."""
    if cfg.provider == "anthropic":
        from strands.models.anthropic import AnthropicModel  # imported lazily: optional dependency
        return AnthropicModel(client_args={"api_key": cfg.api_key}, model_id=cfg.model, max_tokens=16000)

    from strands.models.openai import OpenAIModel
    client_args = {"api_key": cfg.api_key or "missing-key"}
    if cfg.provider == "openai_compatible" and cfg.base_url:
        client_args["base_url"] = cfg.base_url
    return OpenAIModel(client_args=client_args, model_id=cfg.model)
