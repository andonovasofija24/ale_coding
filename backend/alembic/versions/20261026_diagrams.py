"""Diagram tasks (UML / ER): pictures of diagrams uploaded by students; submissions remember where the diagram came from

Revision ID: 20261026_diagrams
Revises: 20261025_web
Create Date: 2026-10-26
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20261026_diagrams"
down_revision = "20261025_web"
branch_labels = None
depends_on = None

UUID = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    # a test of a diagram task is one check of the drawing (JSON), not code
    op.execute("ALTER TYPE test_case_type ADD VALUE IF NOT EXISTS 'diagram'")
    op.create_table(
        "diagram_uploads",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("task_id", UUID, sa.ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("file_name", sa.String(255), nullable=False, server_default=""),
        sa.Column("file_type", sa.String(100), nullable=False, server_default=""),
        sa.Column("data", sa.LargeBinary, nullable=False),
        sa.Column("reading", sa.Text, nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime, nullable=True),
    )
    op.create_index("ix_diagram_uploads_user_id", "diagram_uploads", ["user_id"])


def downgrade() -> None:
    # (PostgreSQL can't drop an enum value; diagram tests are removed so nothing uses it)
    op.execute("DELETE FROM test_cases WHERE type::text = 'diagram'")
    op.drop_index("ix_diagram_uploads_user_id", table_name="diagram_uploads")
    op.drop_table("diagram_uploads")
