"""The account type follows the e-mail: …@students.finki.ukim.mk → student, …@finki.ukim.mk → teacher (admins and
other e-mails are left as they are). Who is in which subject is put right at start-up (the study plan).

Revision ID: 20261107_email
Revises: 20261106_perms
"""
import os

from alembic import op
import sqlalchemy as sa

revision = "20261107_email"
down_revision = "20261106_perms"
branch_labels = None
depends_on = None


def _domains(name: str, default: str) -> list[str]:
    return [d.strip().lower().lstrip("@") for d in os.environ.get(name, default).split(",") if d.strip()]


def upgrade():
    conn = op.get_bind()
    for kind, domains in (("student", _domains("STUDENT_EMAIL_DOMAINS", "students.finki.ukim.mk")),
                          ("teacher", _domains("TEACHER_EMAIL_DOMAINS", "finki.ukim.mk"))):
        for d in domains:
            conn.execute(sa.text("UPDATE users SET role = :k WHERE role <> 'admin' AND role <> :k "
                                 "AND lower(split_part(email, '@', 2)) = :d"), {"k": kind, "d": d})


def downgrade():
    pass
