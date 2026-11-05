"""Sprint 13: sequence diagrams — Software Engineering (SI) also has sequence diagram tasks

Revision ID: 20261029_sequence
Revises: 20261028_subjects
Create Date: 2026-10-29
"""
from alembic import op

revision = "20261029_sequence"
down_revision = "20261028_subjects"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""UPDATE subjects SET languages = languages || '["sequence"]'::jsonb
                  WHERE code = 'SI' AND NOT languages ? 'sequence'""")


def downgrade() -> None:
    op.execute("UPDATE subjects SET languages = languages - 'sequence' WHERE code = 'SI'")
