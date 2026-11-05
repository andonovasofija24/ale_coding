"""Students' elective plans and change requests; practice assignments for a colloquium (estimated grade)

Revision ID: 20261103_electives
Revises: 20261102_roles
Create Date: 2026-11-03
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20261103_electives"
down_revision = "20261102_roles"
branch_labels = None
depends_on = None

UID = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    op.create_table(
        "elective_plans",
        sa.Column("user_id", UID, sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("confirmed_at", sa.DateTime(), nullable=True),
    )
    op.create_table(
        "elective_choices",
        sa.Column("id", UID, primary_key=True),
        sa.Column("user_id", UID, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("subject_id", UID, sa.ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("semester", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("user_id", "subject_id", name="uq_elective_choice"),
    )
    op.create_table(
        "elective_requests",
        sa.Column("id", UID, primary_key=True),
        sa.Column("user_id", UID, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("remove_subject_id", UID, sa.ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("remove_semester", sa.Integer(), nullable=False),
        sa.Column("add_subject_id", UID, sa.ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("add_semester", sa.Integer(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("status", sa.String(12), nullable=False, server_default="pending"),
        sa.Column("admin_note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("decided_at", sa.DateTime(), nullable=True),
        sa.Column("decided_by", UID, sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
    )
    op.add_column("assignments", sa.Column("practice_for", sa.String(10), nullable=True))


def downgrade() -> None:
    op.drop_column("assignments", "practice_for")
    op.drop_table("elective_requests")
    op.drop_table("elective_choices")
    op.drop_table("elective_plans")
