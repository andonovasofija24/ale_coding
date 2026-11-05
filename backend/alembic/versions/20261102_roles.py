"""Roles: a course role the admin set is locked (Moodle / LTI doesn't change it); the professor's final grades

Revision ID: 20261102_roles
Revises: 20261101_finki
Create Date: 2026-11-02
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20261102_roles"
down_revision = "20261101_finki"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("course_members", sa.Column("role_locked", sa.Boolean(), nullable=False, server_default=sa.false()))
    # {user_id: {"grade": 5..10, "by": user_id, "at": iso}}
    op.add_column("courses", sa.Column("final_grades", postgresql.JSONB(), nullable=False, server_default="{}"))


def downgrade() -> None:
    op.drop_column("courses", "final_grades")
    op.drop_column("course_members", "role_locked")
