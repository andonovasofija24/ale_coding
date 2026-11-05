"""Platform operations: AI provider settings (bring your own key) and observability events."""
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Text, Integer, Boolean, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class AISettings(Base):
    """Single-row table (id = 1): which AI provider/model the whole platform uses, and its API key.

    The key is stored encrypted (Fernet, derived from SECRET_KEY) and is never sent back to clients.
    If there is no row, the platform falls back to OPENAI_API_KEY from the environment and gpt-4o.
    """
    __tablename__ = "ai_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    provider: Mapped[str] = mapped_column(String(32), nullable=False)          # openai | anthropic | openai_compatible
    model: Mapped[str] = mapped_column(String(200), nullable=False)
    base_url: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    api_key_encrypted: Mapped[str] = mapped_column(Text, nullable=False, default="")
    key_hint: Mapped[str] = mapped_column(String(32), nullable=False, default="")  # e.g. "sk-…a1b2"
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)


class Event(Base):
    """One observed operation: an AI call or a test run. Written outside the request transaction."""
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    kind: Mapped[str] = mapped_column(String(16), nullable=False)        # ai | tests
    operation: Mapped[str] = mapped_column(String(32), nullable=False)   # next_step | evaluate | hint | explain | visualize | test_connection | run_tests
    ok: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    provider: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    model: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    input_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    prog_language: Mapped[str] = mapped_column(String(16), nullable=False, default="")
    error: Mapped[str] = mapped_column(Text, nullable=False, default="")
    request_id: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    task_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    session_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    extra: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)  # e.g. {"passed": 2, "total": 3}

    __table_args__ = (
        Index("ix_events_created_at", "created_at"),
        Index("ix_events_kind_created", "kind", "created_at"),
    )
