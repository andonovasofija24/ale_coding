"""AI policy per assignment, exam mode (attempts, timer, IPs, events), task variants, manual grading, code comments

Revision ID: 20261021_exams
Revises: 20261020_courses
Create Date: 2026-10-21
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20261021_exams"
down_revision = "20261020_courses"
branch_labels = None
depends_on = None

UUID = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    add = lambda *cols: [op.add_column("assignments", c) for c in cols]
    add(
        sa.Column("ai_mode", sa.String(10), nullable=False, server_default="full"),
        sa.Column("hint_limit", sa.Integer, nullable=False, server_default="3"),
        sa.Column("exam", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("duration_minutes", sa.Integer, nullable=True),
        sa.Column("allowed_ips", sa.Text, nullable=False, server_default=""),
        sa.Column("results_visibility", sa.String(10), nullable=False, server_default="full"),
        sa.Column("scores_after_publish", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("grades_published", sa.Boolean, nullable=False, server_default=sa.false()),
    )
    op.add_column("assignment_tasks", sa.Column("variant_group", sa.Integer, nullable=True))

    op.create_table(
        "assignment_attempts",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("assignment_id", UUID, sa.ForeignKey("assignments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("started_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("ends_at", sa.DateTime, nullable=True),
        sa.Column("finished_at", sa.DateTime, nullable=True),
        sa.Column("ip", sa.String(64), nullable=False, server_default=""),
        sa.UniqueConstraint("assignment_id", "user_id", name="uq_attempt"),
    )
    op.create_table(
        "exam_events",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("assignment_id", UUID, sa.ForeignKey("assignments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("task_id", UUID, nullable=True),
        sa.Column("kind", sa.String(20), nullable=False),
        sa.Column("detail", sa.Text, nullable=False, server_default=""),
        sa.Column("ip", sa.String(64), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_exam_events_lookup", "exam_events", ["assignment_id", "user_id", "created_at"])
    op.create_table(
        "task_grades",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("assignment_id", UUID, sa.ForeignKey("assignments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("task_id", UUID, sa.ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("adjust", sa.Float, nullable=False, server_default="0"),
        sa.Column("override", sa.Float, nullable=True),
        sa.Column("comment", sa.Text, nullable=False, server_default=""),
        sa.Column("graded_by", UUID, sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("assignment_id", "task_id", "user_id", name="uq_task_grade"),
    )
    op.create_table(
        "code_comments",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("submission_id", UUID, sa.ForeignKey("submissions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("line", sa.Integer, nullable=False),
        sa.Column("body", sa.Text, nullable=False),
        sa.Column("author_id", UUID, sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_code_comments_submission_id", "code_comments", ["submission_id"])


def downgrade() -> None:
    op.drop_index("ix_code_comments_submission_id", table_name="code_comments")
    op.drop_table("code_comments")
    op.drop_table("task_grades")
    op.drop_index("ix_exam_events_lookup", table_name="exam_events")
    op.drop_table("exam_events")
    op.drop_table("assignment_attempts")
    op.drop_column("assignment_tasks", "variant_group")
    for c in ("grades_published", "scores_after_publish", "results_visibility", "allowed_ips", "duration_minutes",
              "exam", "hint_limit", "ai_mode"):
        op.drop_column("assignments", c)
