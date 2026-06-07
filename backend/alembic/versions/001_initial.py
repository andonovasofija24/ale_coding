"""initial schema

Revision ID: 001
Revises:
Create Date: 2024-01-01
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("role", sa.Enum("student", "admin", name="user_role"), nullable=False, server_default="student"),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "tasks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("starter_code", sa.Text, nullable=False, server_default=""),
        sa.Column("model_solution", sa.Text, nullable=False),
        sa.Column("language", sa.String(50), nullable=False, server_default="cpp"),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "test_cases",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("task_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("type", sa.Enum("code_sample", "stdin_stdout", name="test_case_type"), nullable=False),
        sa.Column("test_code", sa.Text, nullable=False, server_default=""),
        sa.Column("stdin", sa.Text, nullable=False, server_default=""),
        sa.Column("expected_output", sa.Text, nullable=False),
        sa.Column("is_hidden", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("order", sa.Integer, nullable=False, server_default="0"),
    )

    op.create_table(
        "sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("task_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tasks.id"), nullable=False),
        sa.Column("status", sa.Enum("in_progress", "completed", name="session_status"), nullable=False, server_default="in_progress"),
        sa.Column("current_step", sa.Integer, nullable=False, server_default="0"),
        sa.Column("current_code", sa.Text, nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "session_steps",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("step_number", sa.Integer, nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("step_type", sa.Enum("correctness", "optimization", name="step_type"), nullable=False, server_default="correctness"),
        sa.Column("status", sa.Enum("pending", "active", "completed", name="step_status"), nullable=False, server_default="pending"),
        sa.Column("agent_feedback", sa.Text, nullable=False, server_default=""),
    )

    op.create_table(
        "step_attempts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("step_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("session_steps.id", ondelete="CASCADE"), nullable=False),
        sa.Column("code", sa.Text, nullable=False),
        sa.Column("submitted_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("passed", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("feedback", sa.Text, nullable=False, server_default=""),
    )


def downgrade() -> None:
    op.drop_table("step_attempts")
    op.drop_table("session_steps")
    op.drop_table("sessions")
    op.drop_table("test_cases")
    op.drop_table("tasks")
    op.drop_table("users")
    op.execute("DROP TYPE IF EXISTS step_status")
    op.execute("DROP TYPE IF EXISTS step_type")
    op.execute("DROP TYPE IF EXISTS session_status")
    op.execute("DROP TYPE IF EXISTS test_case_type")
    op.execute("DROP TYPE IF EXISTS user_role")
