"""Subjects: electives can have a semester too; Object-Oriented Analysis and Design (ООАД) holds the UML diagrams

Revision ID: 20261031_ooaid
Revises: 20261030_lti
Create Date: 2026-10-31
"""
import json
import uuid

import sqlalchemy as sa
from alembic import op

revision = "20261031_ooaid"
down_revision = "20261030_lti"
branch_labels = None
depends_on = None

UML = ["uml", "usecase", "sequence", "state", "activity", "component", "package", "deployment"]


def upgrade() -> None:
    op.add_column("subjects", sa.Column("elective", sa.Boolean, nullable=False, server_default="false"))
    op.execute("UPDATE subjects SET elective = true WHERE semester IS NULL")

    conn = op.get_bind()
    if not conn.execute(sa.text("SELECT 1 FROM subjects LIMIT 1")).first():
        return  # a new installation: seed.py adds every subject, ООАД included
    # an existing one: add ООАД (or use one the admin already made) and move the UML diagram tasks there
    row = conn.execute(sa.text("""SELECT id FROM subjects WHERE code = 'OOAID'
                                  OR lower(name) LIKE '%анализа и дизајн%' AND lower(name) LIKE '%објектно%'
                                  ORDER BY (code = 'OOAID') DESC LIMIT 1""")).first()
    if row:
        sid = row[0]
        conn.execute(sa.text("""UPDATE subjects SET languages = (SELECT to_jsonb(array_agg(DISTINCT x))
                                FROM jsonb_array_elements_text(languages || CAST(:l AS jsonb)) x) WHERE id = :id"""),
                     {"l": json.dumps(UML), "id": sid})
    else:
        sid = uuid.uuid4()
        pos = conn.execute(sa.text("SELECT position FROM subjects WHERE code = 'SI'")).scalar() or 0
        conn.execute(sa.text("""INSERT INTO subjects (id, code, name, name_en, semester, elective, languages, icon, color,
                                description, position)
                                VALUES (:id, 'OOAID', 'Објектно-ориентирана анализа и дизајн',
                                'Object-Oriented Analysis and Design', 6, false, CAST(:l AS jsonb), 'shapes', '#0B7285', '', :pos)"""),
                     {"id": sid, "l": json.dumps(UML), "pos": pos})
    conn.execute(sa.text("UPDATE tasks SET subject_id = :id WHERE language = ANY(:langs)"), {"id": sid, "langs": UML})
    conn.execute(sa.text("""UPDATE subjects SET languages = (SELECT coalesce(to_jsonb(array_agg(x)), '[]'::jsonb)
                            FROM jsonb_array_elements_text(languages) x WHERE NOT x = ANY(:langs))
                            WHERE code = 'SI'"""), {"langs": UML})


def downgrade() -> None:
    op.drop_column("subjects", "elective")
