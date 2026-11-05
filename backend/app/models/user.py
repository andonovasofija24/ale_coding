import uuid
from datetime import datetime
from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, LargeBinary, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    # Platform role. Professors (and admins) create courses; assistants and professors also author tasks.
    role: Mapped[str] = mapped_column(Enum("student", "admin", "assistant", "professor", name="user_role"), default="student")
    auth_provider: Mapped[str] = mapped_column(String(20), default="password")  # "password" | "microsoft"
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    # Profile picture: bumped on every upload (part of the image URL, so browsers never show an old one). None = no picture.
    avatar_version: Mapped[int | None] = mapped_column(Integer, nullable=True)


class UserProfile(Base):
    """What a person tells about themself. Staff: title, office, consultation hours, bio. Students: index, programme.
    Only what the platform needs — no birthday, address or phone (data minimisation)."""
    __tablename__ = "user_profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    avatar: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    avatar_type: Mapped[str] = mapped_column(String(30), default="")
    title: Mapped[str] = mapped_column(String(120), default="")           # e.g. "Associate professor"
    bio: Mapped[str] = mapped_column(Text, default="")
    office: Mapped[str] = mapped_column(String(120), default="")
    consultation_hours: Mapped[str] = mapped_column(String(300), default="")
    website: Mapped[str] = mapped_column(String(300), default="")
    index_number: Mapped[str] = mapped_column(String(30), default="")     # student index, e.g. 211234
    study_program: Mapped[str] = mapped_column(String(200), default="")
    study_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    show_email: Mapped[bool] = mapped_column(Boolean, default=True)
    email_reminders: Mapped[bool] = mapped_column(Boolean, default=True)  # deadline reminders by e-mail
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class UserAIKey(Base):
    """A person's own AI provider and key ("bring your own key" for one user). Their AI help (tutor, hints,
    visualizations…) then runs on it instead of the platform's key. The key is encrypted like the platform key."""
    __tablename__ = "user_ai_keys"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    model: Mapped[str] = mapped_column(String(120), default="")
    base_url: Mapped[str] = mapped_column(String(500), default="")
    api_key_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    key_hint: Mapped[str] = mapped_column(String(40), default="")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
