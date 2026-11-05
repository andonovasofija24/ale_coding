import uuid
from datetime import datetime
from sqlalchemy import String, Text, Boolean, Integer, ForeignKey, DateTime, Enum, LargeBinary
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB, UUID

from app.database import Base


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    starter_code: Mapped[str] = mapped_column(Text, nullable=False, default="")
    model_solution: Mapped[str] = mapped_column(Text, nullable=False, default="")
    language: Mapped[str] = mapped_column(String(50), default="cpp")
    # What the student hands in: "code" (editor + automatic tests), "document" (PDF/Word/picture, e.g. a diagram),
    # "project" (a zip with several files, reviewed by staff) or "offline" (nothing: done elsewhere, staff enter points).
    kind: Mapped[str] = mapped_column(String(12), nullable=False, default="code")
    # The language title/description are written in, and translations: {"mk": {"title": ..., "description": ...}}
    content_lang: Mapped[str] = mapped_column(String(2), nullable=False, default="en")
    translations: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    # Grading criteria for staff: [{"id": "c1", "title": "Classes", "points": 4}, ...]
    rubric: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    # Public tasks are in the practice collection; non-public ones are seen only through a course assignment.
    is_public: Mapped[bool] = mapped_column(Boolean, default=True)
    # The subject (предмет) the task belongs to; None = not sorted yet.
    subject_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("subjects.id", ondelete="SET NULL"), nullable=True)
    # An AI practice task made for one student (with their own AI key): only they see it; it is not in the bank.
    generated_for: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    test_cases: Mapped[list["TestCase"]] = relationship("TestCase", back_populates="task", cascade="all, delete-orphan", order_by="TestCase.order")


class TaskFile(Base):
    """The teacher's reference solution for a document/project task (a file). Only staff ever see it."""
    __tablename__ = "task_files"

    task_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="CASCADE"), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size: Mapped[int] = mapped_column(Integer, nullable=False)
    data: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class TestCase(Base):
    __tablename__ = "test_cases"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tasks.id"), nullable=False)
    type: Mapped[str] = mapped_column(Enum("code_sample", "stdin_stdout", "diagram", name="test_case_type"), nullable=False)
    test_code: Mapped[str] = mapped_column(Text, default="")
    stdin: Mapped[str] = mapped_column(Text, default="")
    expected_output: Mapped[str] = mapped_column(Text, nullable=False)
    is_hidden: Mapped[bool] = mapped_column(Boolean, default=False)
    order: Mapped[int] = mapped_column(Integer, default=0)

    task: Mapped["Task"] = relationship("Task", back_populates="test_cases")


class DiagramUpload(Base):
    """A picture or PDF of a diagram that a student uploaded instead of drawing it in the editor. The AI reading of it
    goes into the editor; when the student submits, the original file is kept with the submission for the teacher."""
    __tablename__ = "diagram_uploads"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    task_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    file_type: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    data: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    reading: Mapped[str] = mapped_column(Text, nullable=False, default="")  # the diagram the AI read (JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Subject(Base):
    """A FINKI subject (предмет), e.g. Структурно програмирање. Tasks, courses and AI practice are grouped by it."""
    __tablename__ = "subjects"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    finki_code: Mapped[str | None] = mapped_column(String(20), unique=True, nullable=True)  # e.g. F23L1W020
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    name_en: Mapped[str] = mapped_column(String(200), default="")
    semester: Mapped[int | None] = mapped_column(Integer, nullable=True)   # the semester it is taught in; None = any
    elective: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")  # изборен
    languages: Mapped[list] = mapped_column(JSONB, default=list)          # what its tasks are written in
    icon: Mapped[str] = mapped_column(String(40), default="book-open")
    color: Mapped[str] = mapped_column(String(9), default="#2747C9")
    description: Mapped[str] = mapped_column(Text, default="")
    position: Mapped[int] = mapped_column(Integer, default=0)
