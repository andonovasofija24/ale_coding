"""E-mail (drafts, approval, deliveries), deadline reminders, grading scheme and rules, teaching language,
assignment categories, course materials

Revision ID: 20261024_comms
Revises: 20261023_task_kinds
Create Date: 2026-10-24
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20261024_comms"
down_revision = "20261023_task_kinds"
branch_labels = None
depends_on = None

UUID = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    op.add_column("courses", sa.Column("language", sa.String(2), nullable=False, server_default="mk"))
    op.add_column("courses", sa.Column("grading", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")))
    op.add_column("courses", sa.Column("reminders_enabled", sa.Boolean, nullable=False, server_default=sa.true()))
    op.add_column("courses", sa.Column("reminder_hours", sa.Integer, nullable=False, server_default="24"))
    op.add_column("course_groups", sa.Column("language", sa.String(2), nullable=True))
    op.add_column("assignments", sa.Column("category", sa.String(10), nullable=True))
    op.add_column("user_profiles", sa.Column("email_reminders", sa.Boolean, nullable=False, server_default=sa.true()))
    op.create_table(
        "emails",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("course_id", UUID, sa.ForeignKey("courses.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("assignment_id", UUID, sa.ForeignKey("assignments.id", ondelete="SET NULL"), nullable=True),
        sa.Column("kind", sa.String(20), nullable=False),
        sa.Column("audience", sa.String(10), nullable=False, server_default="students"),
        sa.Column("group_id", UUID, sa.ForeignKey("course_groups.id", ondelete="SET NULL"), nullable=True),
        sa.Column("subject_mk", sa.String(300), nullable=False, server_default=""),
        sa.Column("body_mk", sa.Text, nullable=False, server_default=""),
        sa.Column("subject_en", sa.String(300), nullable=False, server_default=""),
        sa.Column("body_en", sa.Text, nullable=False, server_default=""),
        sa.Column("status", sa.String(10), nullable=False, server_default="draft"),
        sa.Column("created_by", UUID, sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("approved_by", UUID, sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("sent_at", sa.DateTime, nullable=True),
        sa.Column("recipients", sa.Integer, nullable=False, server_default="0"),
        sa.Column("failed", sa.Integer, nullable=False, server_default="0"),
        sa.Column("attachment_name", sa.String(255), nullable=False, server_default=""),
        sa.Column("attachment_type", sa.String(100), nullable=False, server_default=""),
        sa.Column("attachment", sa.LargeBinary, nullable=True),
    )
    op.create_table(
        "email_deliveries",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("email_id", UUID, sa.ForeignKey("emails.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True),
        sa.Column("address", sa.String(255), nullable=False),
        sa.Column("lang", sa.String(2), nullable=False, server_default="mk"),
        sa.Column("status", sa.String(10), nullable=False, server_default="queued"),
        sa.Column("error", sa.Text, nullable=False, server_default=""),
        sa.Column("sent_at", sa.DateTime, nullable=True),
    )
    op.create_table(
        "reminder_log",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("assignment_id", UUID, sa.ForeignKey("assignments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sent_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("assignment_id", "user_id", name="uq_reminder"),
    )
    op.create_table(
        "course_materials",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("course_id", UUID, sa.ForeignKey("courses.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("section", sa.String(10), nullable=False, server_default="lecture"),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("week", sa.Integer, nullable=True),
        sa.Column("position", sa.Integer, nullable=False, server_default="0"),
        sa.Column("published", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("file_name", sa.String(255), nullable=False),
        sa.Column("file_type", sa.String(100), nullable=False),
        sa.Column("file_size", sa.Integer, nullable=False),
        sa.Column("has_preview", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("created_by", UUID, sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    op.create_table(
        "material_files",
        sa.Column("material_id", UUID, sa.ForeignKey("course_materials.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("data", sa.LargeBinary, nullable=False),
        sa.Column("preview", sa.LargeBinary, nullable=True),
    )


def downgrade() -> None:
    for t in ("material_files", "course_materials", "reminder_log", "email_deliveries", "emails"):
        op.drop_table(t)
    op.drop_column("user_profiles", "email_reminders")
    op.drop_column("assignments", "category")
    op.drop_column("course_groups", "language")
    for c in ("reminder_hours", "reminders_enabled", "grading", "language"):
        op.drop_column("courses", c)
