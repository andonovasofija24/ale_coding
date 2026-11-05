"""HTML/CSS/JS tasks; editor diagnostics can be turned off per assignment

Revision ID: 20261025_web
Revises: 20261024_comms
Create Date: 2026-10-25
"""
from alembic import op
import sqlalchemy as sa

revision = "20261025_web"
down_revision = "20261024_comms"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("assignments", sa.Column("editor_checks", sa.Boolean, nullable=False, server_default=sa.true()))


def downgrade() -> None:
    op.drop_column("assignments", "editor_checks")
