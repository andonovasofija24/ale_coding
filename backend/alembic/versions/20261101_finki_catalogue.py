"""Subjects: the official FINKI code (the catalogue itself is merged once by seed.py from finki_subjects.csv)

Revision ID: 20261101_finki
Revises: 20261031_ooaid
Create Date: 2026-11-01
"""
import sqlalchemy as sa
from alembic import op

revision = "20261101_finki"
down_revision = "20261031_ooaid"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("subjects", sa.Column("finki_code", sa.String(20), nullable=True))
    op.create_unique_constraint("uq_subjects_finki_code", "subjects", ["finki_code"])


def downgrade() -> None:
    op.drop_constraint("uq_subjects_finki_code", "subjects")
    op.drop_column("subjects", "finki_code")
