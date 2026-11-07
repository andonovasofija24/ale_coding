"""Logs: events also carry the course they happened in; indexes for reading them by person / course

Revision ID: 20261105_logs
Revises: 20261104_prog
Create Date: 2026-11-05
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20261105_logs"
down_revision = "20261104_prog"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("events", sa.Column("course_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_index("ix_events_user_created", "events", ["user_id", "created_at"])
    op.create_index("ix_events_course_created", "events", ["course_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_events_course_created", table_name="events")
    op.drop_index("ix_events_user_created", table_name="events")
    op.drop_column("events", "course_id")
