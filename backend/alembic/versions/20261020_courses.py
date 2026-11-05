"""Courses, groups, members, assignments with deadlines, submissions; staff roles; task visibility; SSO users

Revision ID: 20261020_courses
Revises: 20261019_ops
Create Date: 2026-10-20
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20261020_courses"
down_revision = "20261019_ops"
branch_labels = None
depends_on = None

UUID = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    # Platform roles: student | assistant | professor | admin
    op.execute("ALTER TYPE user_role ADD VALUE IF NOT EXISTS 'assistant'")
    op.execute("ALTER TYPE user_role ADD VALUE IF NOT EXISTS 'professor'")
    # "password" or "microsoft" (users created by Microsoft sign-in have no usable password)
    op.add_column("users", sa.Column("auth_provider", sa.String(20), nullable=False, server_default="password"))
    # Public tasks are in the practice collection; the others are seen only through a course assignment
    op.add_column("tasks", sa.Column("is_public", sa.Boolean, nullable=False, server_default=sa.true()))

    op.create_table(
        "courses",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("code", sa.String(50), nullable=False),
        sa.Column("name", sa.String(300), nullable=False),
        sa.Column("semester", sa.String(100), nullable=False, server_default=""),
        sa.Column("description", sa.Text, nullable=False, server_default=""),
        sa.Column("join_code", sa.String(20), nullable=False, unique=True),
        sa.Column("join_enabled", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("archived", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("created_by", UUID, sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    op.create_table(
        "course_groups",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("course_id", UUID, sa.ForeignKey("courses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
    )
    op.create_table(
        "course_members",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("course_id", UUID, sa.ForeignKey("courses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.String(20), nullable=False, server_default="student"),
        sa.Column("group_id", UUID, sa.ForeignKey("course_groups.id", ondelete="SET NULL"), nullable=True),
        sa.Column("joined_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("course_id", "user_id", name="uq_course_member"),
    )
    op.create_index("ix_course_members_user", "course_members", ["user_id"])
    op.create_table(
        "assignments",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("course_id", UUID, sa.ForeignKey("courses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("description", sa.Text, nullable=False, server_default=""),
        sa.Column("kind", sa.String(20), nullable=False, server_default="lab"),
        sa.Column("group_id", UUID, sa.ForeignKey("course_groups.id", ondelete="SET NULL"), nullable=True),
        sa.Column("opens_at", sa.DateTime, nullable=True),
        sa.Column("due_at", sa.DateTime, nullable=True),
        sa.Column("allow_late", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("late_penalty", sa.Integer, nullable=False, server_default="0"),
        sa.Column("published", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("created_by", UUID, sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_assignments_course", "assignments", ["course_id"])
    op.create_table(
        "assignment_tasks",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("assignment_id", UUID, sa.ForeignKey("assignments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("task_id", UUID, sa.ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("points", sa.Float, nullable=False, server_default="10"),
        sa.Column("order", sa.Integer, nullable=False, server_default="0"),
        sa.UniqueConstraint("assignment_id", "task_id", name="uq_assignment_task"),
    )
    op.create_table(
        "submissions",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("assignment_id", UUID, sa.ForeignKey("assignments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("task_id", UUID, sa.ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("code", sa.Text, nullable=False),
        sa.Column("passed", sa.Integer, nullable=False),
        sa.Column("total", sa.Integer, nullable=False),
        sa.Column("score", sa.Float, nullable=False),
        sa.Column("late", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("submitted_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_submissions_lookup", "submissions", ["assignment_id", "user_id", "task_id"])


def downgrade() -> None:
    op.drop_index("ix_submissions_lookup", table_name="submissions")
    op.drop_table("submissions")
    op.drop_table("assignment_tasks")
    op.drop_index("ix_assignments_course", table_name="assignments")
    op.drop_table("assignments")
    op.drop_index("ix_course_members_user", table_name="course_members")
    op.drop_table("course_members")
    op.drop_table("course_groups")
    op.drop_table("courses")
    op.drop_column("tasks", "is_public")
    op.drop_column("users", "auth_provider")
    # PostgreSQL can't drop enum values; staff accounts go back to "student".
    op.execute("UPDATE users SET role = 'student' WHERE role IN ('assistant', 'professor')")
