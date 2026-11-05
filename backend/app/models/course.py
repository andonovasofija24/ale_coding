"""Courses, groups, members, assignments (labs / homework with deadlines) and graded submissions."""
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Text, Integer, Boolean, DateTime, ForeignKey, Float, UniqueConstraint, Index, LargeBinary, false
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

COURSE_ROLES = ("teacher", "assistant", "lab", "student")  # lab = лаборант: sees and grades labs
ASSIGNMENT_KINDS = ("lab", "homework", "practice", "exam")
AI_MODES = ("full", "hints", "off")              # strictest wins when a task is in several active assignments
RESULTS_VISIBILITY = ("full", "summary", "none")  # what a student sees right after "Submit"


class Course(Base):
    __tablename__ = "courses"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(50), nullable=False)            # e.g. "SP"
    name: Mapped[str] = mapped_column(String(300), nullable=False)           # e.g. "Структурно програмирање"
    semester: Mapped[str] = mapped_column(String(100), nullable=False, default="")  # e.g. "2026/27 зимски"
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    join_code: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    join_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    archived: Mapped[bool] = mapped_column(Boolean, default=False)
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    language: Mapped[str] = mapped_column(String(2), nullable=False, default="mk")  # teaching language (groups may differ)
    # {"weights": {category: %}, "thresholds": [6, 7, 8, 9, 10 from %], "rules": [{"type", "enabled", "value"}]}
    grading: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    # the professor's final grades: {user_id: {"grade": 5..10, "by": user_id, "at": iso}}
    final_grades: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict, server_default="{}")
    reminders_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    reminder_hours: Mapped[int] = mapped_column(Integer, nullable=False, default=24)
    # Which FINKI subject this course is a run of (e.g. СП 2026/27 is Структурно програмирање).
    subject_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("subjects.id", ondelete="SET NULL"), nullable=True)

    groups: Mapped[list["CourseGroup"]] = relationship("CourseGroup", cascade="all, delete-orphan", order_by="CourseGroup.name")


class CourseGroup(Base):
    __tablename__ = "course_groups"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    course_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    language: Mapped[Optional[str]] = mapped_column(String(2), nullable=True)  # e.g. the English group; None = course language


class CourseMember(Base):
    __tablename__ = "course_members"
    __table_args__ = (UniqueConstraint("course_id", "user_id", name="uq_course_member"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    course_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="student")  # teacher | assistant | lab | student
    # set by the admin in ALE: Moodle (LTI launches / roster) no longer changes it
    role_locked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=false())
    group_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("course_groups.id", ondelete="SET NULL"), nullable=True)
    joined_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Assignment(Base):
    __tablename__ = "assignments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    course_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    kind: Mapped[str] = mapped_column(String(20), nullable=False, default="lab")  # lab | homework | practice
    group_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("course_groups.id", ondelete="SET NULL"), nullable=True)  # None = whole course
    opens_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)   # UTC; None = open now
    due_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)     # UTC; None = no deadline
    allow_late: Mapped[bool] = mapped_column(Boolean, default=False)
    late_penalty: Mapped[int] = mapped_column(Integer, default=0)  # percent taken off a late submission
    published: Mapped[bool] = mapped_column(Boolean, default=False)
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # AI tutor while the assignment is active: full | hints (only N task hints) | off
    ai_mode: Mapped[str] = mapped_column(String(10), nullable=False, default="full")
    hint_limit: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    # Exam: each student starts it themselves and gets `duration_minutes` from that moment (capped by due_at)
    exam: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    duration_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    allowed_ips: Mapped[str] = mapped_column(Text, nullable=False, default="")  # CIDRs, comma/space separated; "" = any
    results_visibility: Mapped[str] = mapped_column(String(10), nullable=False, default="full")
    # Points (and teacher comments) are shown to students only after "Publish grades" when this is True
    scores_after_publish: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    grades_published: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # "More points possible": tell a student whose submission passes at least this % of the tests (but not all)
    # that the teacher may review it, and mark it for review. 0 = off.
    review_threshold: Mapped[int] = mapped_column(Integer, nullable=False, default=85)
    # Where its points count in the course grade: labs / homework / k1 / k2 / exam / none. None = from the kind.
    category: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    # A practice assignment made as preparation for a colloquium / the exam (k1 | k2 | exam): it never counts in the
    # grade, but the students' results in it feed their estimated grade.
    practice_for: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    # AI suggestions for improving a solution that already passes every test, per task and student (hints mode).
    improve_limit: Mapped[int] = mapped_column(Integer, nullable=False, default=2)
    # sprint 8: compiler errors underlined in the editor while typing (a teacher may turn them off for an exam)
    editor_checks: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")

    tasks: Mapped[list["AssignmentTask"]] = relationship("AssignmentTask", cascade="all, delete-orphan", order_by="AssignmentTask.order")


class AssignmentTask(Base):
    __tablename__ = "assignment_tasks"
    __table_args__ = (UniqueConstraint("assignment_id", "task_id", name="uq_assignment_task"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    assignment_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("assignments.id", ondelete="CASCADE"), nullable=False)
    task_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    points: Mapped[float] = mapped_column(Float, nullable=False, default=10)
    order: Mapped[int] = mapped_column(Integer, default=0)
    # Tasks with the same variant group are alternatives: each student gets one of them (stable per student)
    variant_group: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)


class Submission(Base):
    """One "Submit" of a student's code for a task in an assignment: all tests (hidden too) run, points computed."""
    __tablename__ = "submissions"
    __table_args__ = (Index("ix_submissions_lookup", "assignment_id", "user_id", "task_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    assignment_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("assignments.id", ondelete="CASCADE"), nullable=False)
    task_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    code: Mapped[str] = mapped_column(Text, nullable=False)
    passed: Mapped[int] = mapped_column(Integer, nullable=False)
    total: Mapped[int] = mapped_column(Integer, nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)     # points after any late penalty
    late: Mapped[bool] = mapped_column(Boolean, default=False)
    submitted_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)  # when it was received
    # Queue: received ("pending") -> being tested ("running") -> "done" (or "error" after repeated failures).
    status: Mapped[str] = mapped_column(String(10), nullable=False, default="done")
    results: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)  # {"staff": [...], "student": [...]}
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error: Mapped[str] = mapped_column(Text, nullable=False, default="")
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    # an uploaded file (document / project tasks); its bytes are in SubmissionFile
    file_name: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    file_type: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    file_size: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class SubmissionFile(Base):
    """The uploaded file of a submission, kept apart so lists of submissions stay light."""
    __tablename__ = "submission_files"

    submission_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("submissions.id", ondelete="CASCADE"), primary_key=True)
    data: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)


class AssignmentAttempt(Base):
    """A student's start of an exam: the personal deadline is fixed at the start."""
    __tablename__ = "assignment_attempts"
    __table_args__ = (UniqueConstraint("assignment_id", "user_id", name="uq_attempt"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    assignment_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("assignments.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    ends_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)  # None = until the assignment's due_at
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)  # the student pressed "Finish"
    ip: Mapped[str] = mapped_column(String(64), nullable=False, default="")


class ExamEvent(Base):
    """What happened during an exam: start, submit, finish, left the tab, large paste, IP change."""
    __tablename__ = "exam_events"
    __table_args__ = (Index("ix_exam_events_lookup", "assignment_id", "user_id", "created_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    assignment_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("assignments.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    task_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    kind: Mapped[str] = mapped_column(String(20), nullable=False)
    detail: Mapped[str] = mapped_column(Text, nullable=False, default="")
    ip: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class TaskGrade(Base):
    """Staff review of a student's work on one task of an assignment: an adjustment or override and a comment."""
    __tablename__ = "task_grades"
    __table_args__ = (UniqueConstraint("assignment_id", "task_id", "user_id", name="uq_task_grade"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    assignment_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("assignments.id", ondelete="CASCADE"), nullable=False)
    task_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    adjust: Mapped[float] = mapped_column(Float, nullable=False, default=0)        # added to the automatic points
    override: Mapped[Optional[float]] = mapped_column(Float, nullable=True)      # replaces them when set
    comment: Mapped[str] = mapped_column(Text, nullable=False, default="")
    rubric_scores: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)  # {criterion id: points}
    graded_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class CodeComment(Base):
    """A staff comment on one line of a submission (like a code review)."""
    __tablename__ = "code_comments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    submission_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("submissions.id", ondelete="CASCADE"), nullable=False, index=True)
    line: Mapped[int] = mapped_column(Integer, nullable=False)
    path: Mapped[str] = mapped_column(String(500), nullable=False, default="")  # file inside a project zip
    body: Mapped[str] = mapped_column(Text, nullable=False)
    author_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


ATTENDANCE = ("present", "absent", "excused")


class Attendance(Base):
    """Was the student at this lab session (for labs done on site / elsewhere, and for signature rules later)."""
    __tablename__ = "attendance"
    __table_args__ = (UniqueConstraint("assignment_id", "user_id", name="uq_attendance"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    assignment_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("assignments.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    status: Mapped[str] = mapped_column(String(10), nullable=False)
    updated_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
