"""User profiles (picture, bio, office hours, index), submission queue, review threshold, improvement limit

Revision ID: 20261022_profiles
Revises: 20261021_exams
Create Date: 2026-10-22
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20261022_profiles"
down_revision = "20261021_exams"
branch_labels = None
depends_on = None

UUID = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    op.add_column("assignments", sa.Column("review_threshold", sa.Integer, nullable=False, server_default="85"))
    op.add_column("assignments", sa.Column("improve_limit", sa.Integer, nullable=False, server_default="2"))
    for col in (
        sa.Column("status", sa.String(10), nullable=False, server_default="done"),
        sa.Column("results", postgresql.JSONB, nullable=True),
        sa.Column("attempts", sa.Integer, nullable=False, server_default="0"),
        sa.Column("error", sa.Text, nullable=False, server_default=""),
        sa.Column("started_at", sa.DateTime, nullable=True),
        sa.Column("finished_at", sa.DateTime, nullable=True),
    ):
        op.add_column("submissions", col)
    # the queue picks the oldest waiting submission
    op.create_index("ix_submissions_queue", "submissions", ["status", "submitted_at"],
                    postgresql_where=sa.text("status IN ('pending', 'running')"))
    op.add_column("users", sa.Column("avatar_version", sa.Integer, nullable=True))
    op.create_table(
        "user_profiles",
        sa.Column("user_id", UUID, sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("avatar", sa.LargeBinary, nullable=True),
        sa.Column("avatar_type", sa.String(30), nullable=False, server_default=""),
        sa.Column("title", sa.String(120), nullable=False, server_default=""),
        sa.Column("bio", sa.Text, nullable=False, server_default=""),
        sa.Column("office", sa.String(120), nullable=False, server_default=""),
        sa.Column("consultation_hours", sa.String(300), nullable=False, server_default=""),
        sa.Column("website", sa.String(300), nullable=False, server_default=""),
        sa.Column("index_number", sa.String(30), nullable=False, server_default=""),
        sa.Column("study_program", sa.String(200), nullable=False, server_default=""),
        sa.Column("study_year", sa.Integer, nullable=True),
        sa.Column("show_email", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_index("ix_submissions_queue", table_name="submissions")
    for c in ("finished_at", "started_at", "error", "attempts", "results", "status"):
        op.drop_column("submissions", c)
    op.drop_column("assignments", "improve_limit")
    op.drop_column("assignments", "review_threshold")
    op.drop_table("user_profiles")
    op.drop_column("users", "avatar_version")
