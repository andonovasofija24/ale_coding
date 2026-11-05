"""Sprint 11: personal AI keys, richer tutor steps (why / tip), several solutions of one task

Revision ID: 20261027_sprint11
Revises: 20261026_diagrams
Create Date: 2026-10-27
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20261027_sprint11"
down_revision = "20261026_diagrams"
branch_labels = None
depends_on = None

UUID = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    # a person's own AI provider + key (students too): their AI help then uses it
    op.create_table(
        "user_ai_keys",
        sa.Column("user_id", UUID, sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("provider", sa.String(32), nullable=False),
        sa.Column("model", sa.String(120), nullable=False, server_default=""),
        sa.Column("base_url", sa.String(500), nullable=False, server_default=""),
        sa.Column("api_key_encrypted", sa.Text, nullable=False),
        sa.Column("key_hint", sa.String(40), nullable=False, server_default=""),
        sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    # tutor steps: why the step is needed, and one extra useful fact
    op.add_column("session_steps", sa.Column("why", sa.Text, nullable=False, server_default=""))
    op.add_column("session_steps", sa.Column("tip", sa.Text, nullable=False, server_default=""))
    # one task, several solutions: which one this session is, the approach it follows, what else is possible
    op.add_column("sessions", sa.Column("solution_no", sa.Integer, nullable=False, server_default="1"))
    op.add_column("sessions", sa.Column("approach", sa.Text, nullable=False, server_default=""))
    op.add_column("sessions", sa.Column("alternatives", postgresql.JSONB, nullable=False, server_default="[]"))


def downgrade() -> None:
    op.drop_column("sessions", "alternatives")
    op.drop_column("sessions", "approach")
    op.drop_column("sessions", "solution_no")
    op.drop_column("session_steps", "tip")
    op.drop_column("session_steps", "why")
    op.drop_table("user_ai_keys")
