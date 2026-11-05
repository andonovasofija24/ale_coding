import uuid
from datetime import datetime
from sqlalchemy import String, Text, Integer, ForeignKey, DateTime, Enum, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB, UUID

from app.database import Base


class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    task_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tasks.id"), nullable=False)
    status: Mapped[str] = mapped_column(Enum("in_progress", "completed", name="session_status"), default="in_progress")
    current_step: Mapped[int] = mapped_column(Integer, default=0)
    current_code: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    # Several solutions of one task: this is solution number `solution_no`, following `approach` ("" = the
    # first, free one); when it is finished, `alternatives` lists other ways to solve the task ([{title, idea}]).
    solution_no: Mapped[int] = mapped_column(Integer, default=1)
    approach: Mapped[str] = mapped_column(Text, default="")
    alternatives: Mapped[list] = mapped_column(JSONB, default=list)

    steps: Mapped[list["SessionStep"]] = relationship("SessionStep", back_populates="session", cascade="all, delete-orphan", order_by="SessionStep.step_number")
    attempts: Mapped[list["StepAttempt"]] = relationship("StepAttempt", back_populates="session", cascade="all, delete-orphan")


class SessionStep(Base):
    __tablename__ = "session_steps"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sessions.id"), nullable=False)
    step_number: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    step_type: Mapped[str] = mapped_column(Enum("correctness", "optimization", name="step_type"), default="correctness")
    status: Mapped[str] = mapped_column(Enum("pending", "active", "completed", name="step_status"), default="pending")
    agent_feedback: Mapped[str] = mapped_column(Text, default="")
    why: Mapped[str] = mapped_column(Text, default="")   # why this step: its purpose, how it moves towards the solution
    tip: Mapped[str] = mapped_column(Text, default="")   # one extra useful fact (a concept, a pitfall, real-world use)

    session: Mapped["Session"] = relationship("Session", back_populates="steps")


class StepAttempt(Base):
    __tablename__ = "step_attempts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sessions.id"), nullable=False)
    step_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("session_steps.id"), nullable=False)
    code: Mapped[str] = mapped_column(Text, nullable=False)
    submitted_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    passed: Mapped[bool] = mapped_column(Boolean, default=False)
    feedback: Mapped[str] = mapped_column(Text, default="")

    session: Mapped["Session"] = relationship("Session", back_populates="attempts")
