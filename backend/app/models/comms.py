"""E-mail (drafted, approved by a teacher, then sent), deadline reminders, and course materials."""
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, LargeBinary, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base

EMAIL_KINDS = ("announcement", "grades", "deadline", "gradesheet", "custom", "reminder")


class Email(Base):
    """One message to a course (or its staff), in Macedonian and English. Created as a draft; nothing is sent until
    a teacher approves it (reminders excepted — they are automatic)."""
    __tablename__ = "emails"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    course_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("courses.id", ondelete="CASCADE"), nullable=False, index=True)
    assignment_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("assignments.id", ondelete="SET NULL"), nullable=True)
    kind: Mapped[str] = mapped_column(String(20), nullable=False)
    audience: Mapped[str] = mapped_column(String(10), nullable=False, default="students")  # students | staff
    group_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("course_groups.id", ondelete="SET NULL"), nullable=True)
    subject_mk: Mapped[str] = mapped_column(String(300), nullable=False, default="")
    body_mk: Mapped[str] = mapped_column(Text, nullable=False, default="")
    subject_en: Mapped[str] = mapped_column(String(300), nullable=False, default="")
    body_en: Mapped[str] = mapped_column(Text, nullable=False, default="")
    status: Mapped[str] = mapped_column(String(10), nullable=False, default="draft")  # draft | sending | sent | cancelled
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    approved_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    recipients: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    attachment_name: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    attachment_type: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    attachment: Mapped[Optional[bytes]] = mapped_column(LargeBinary, nullable=True)


class EmailDelivery(Base):
    """One recipient of an e-mail: the language they got it in and whether it went out."""
    __tablename__ = "email_deliveries"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("emails.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    address: Mapped[str] = mapped_column(String(255), nullable=False)
    lang: Mapped[str] = mapped_column(String(2), nullable=False, default="mk")
    status: Mapped[str] = mapped_column(String(10), nullable=False, default="queued")  # queued | sent | preview | failed
    error: Mapped[str] = mapped_column(Text, nullable=False, default="")
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class ReminderLog(Base):
    """A deadline reminder already sent to a student for an assignment (never twice, even with several servers)."""
    __tablename__ = "reminder_log"
    __table_args__ = (UniqueConstraint("assignment_id", "user_id", name="uq_reminder"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    assignment_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("assignments.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    sent_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


MATERIAL_SECTIONS = ("lecture", "exercise", "other")


class CourseMaterial(Base):
    """A lecture / exercise presentation or other document of a course."""
    __tablename__ = "course_materials"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    course_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("courses.id", ondelete="CASCADE"), nullable=False, index=True)
    section: Mapped[str] = mapped_column(String(10), nullable=False, default="lecture")
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    week: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    published: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    has_preview: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)  # a PDF to show in the browser
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class MaterialFile(Base):
    __tablename__ = "material_files"

    material_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("course_materials.id", ondelete="CASCADE"), primary_key=True)
    data: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    preview: Mapped[Optional[bytes]] = mapped_column(LargeBinary, nullable=True)  # PDF made from a presentation
