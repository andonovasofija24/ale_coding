"""Every change of a student's electives is a request: a request may only add one, or only take one out.

Revision ID: 20261108_elreq
Revises: 20261107_email
"""
from alembic import op

revision = "20261108_elreq"
down_revision = "20261107_email"
branch_labels = None
depends_on = None


def upgrade():
    for col in ("remove_subject_id", "remove_semester", "add_subject_id", "add_semester"):
        op.alter_column("elective_requests", col, nullable=True)


def downgrade():
    op.execute("DELETE FROM elective_requests WHERE remove_subject_id IS NULL OR add_subject_id IS NULL")
    for col in ("remove_subject_id", "remove_semester", "add_subject_id", "add_semester"):
        op.alter_column("elective_requests", col, nullable=False)
