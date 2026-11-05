"""Sprint 12: subjects (предмети), tasks and courses grouped by them; AI practice tasks owned by one student

Revision ID: 20261028_subjects
Revises: 20261027_sprint11
Create Date: 2026-10-28
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20261028_subjects"
down_revision = "20261027_sprint11"
branch_labels = None
depends_on = None

UUID = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    op.create_table(
        "subjects",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("code", sa.String(20), nullable=False, unique=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("name_en", sa.String(200), nullable=False, server_default=""),
        sa.Column("semester", sa.Integer, nullable=True),
        sa.Column("languages", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("icon", sa.String(40), nullable=False, server_default="book-open"),
        sa.Column("color", sa.String(9), nullable=False, server_default="#2747C9"),
        sa.Column("description", sa.Text, nullable=False, server_default=""),
        sa.Column("position", sa.Integer, nullable=False, server_default="0"),
    )
    op.add_column("tasks", sa.Column("subject_id", UUID, sa.ForeignKey("subjects.id", ondelete="SET NULL"), nullable=True))
    # a task the AI made for one student's practice: only they see it, it is not in the bank
    op.add_column("tasks", sa.Column("generated_for", UUID, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=True))
    op.create_index("ix_tasks_subject", "tasks", ["subject_id"])
    op.create_index("ix_tasks_generated_for", "tasks", ["generated_for"])
    op.add_column("courses", sa.Column("subject_id", UUID, sa.ForeignKey("subjects.id", ondelete="SET NULL"), nullable=True))


def downgrade() -> None:
    op.drop_column("courses", "subject_id")
    op.drop_index("ix_tasks_generated_for", "tasks")
    op.drop_index("ix_tasks_subject", "tasks")
    op.drop_column("tasks", "generated_for")
    op.drop_column("tasks", "subject_id")
    op.drop_table("subjects")
