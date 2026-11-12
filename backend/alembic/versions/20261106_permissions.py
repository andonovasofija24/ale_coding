"""No courses to make and no course roles: every subject has one space; teachers get permissions

Revision ID: 20261106_perms
Revises: 20261105_logs
Create Date: 2026-11-06

- accounts: "assistant" / "professor" become "teacher" (student | teacher | admin)
- course_members: a teacher's permissions (the old roles become their template: teacher → professor, assistant,
  lab → лаборант) and how a student got there (source)
- every subject gets exactly one space (a courses row): a course without a subject gets a subject of its own, the
  courses of one subject are merged into the oldest one (assignments, people, groups, materials, mail, LTI links)
"""
import json
import secrets
import uuid

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20261106_perms"
down_revision = "20261105_logs"
branch_labels = None
depends_on = None

ALL = ["labs.view", "labs.manage", "labs.grade", "exams.view", "exams.manage", "exams.grade", "grades.view",
       "grades.final", "grades.rules", "people.view", "materials.manage", "mail.send", "activity.view", "practice.view"]
TEMPLATES = {
    "teacher": ALL,
    "assistant": ["labs.view", "labs.manage", "labs.grade", "exams.view", "exams.manage", "exams.grade", "grades.view",
                  "people.view", "materials.manage", "mail.send", "activity.view", "practice.view"],
    "lab": ["labs.view", "labs.manage", "labs.grade", "practice.view"],
}


def upgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE user_role ADD VALUE IF NOT EXISTS 'teacher'")
    c = op.get_bind()
    c.execute(sa.text("UPDATE users SET role = 'teacher' WHERE role IN ('assistant', 'professor')"))

    op.add_column("course_members", sa.Column("permissions", postgresql.JSONB(), nullable=False, server_default="[]"))
    op.add_column("course_members", sa.Column("source", sa.String(10), nullable=False, server_default="admin"))
    for old, perms in TEMPLATES.items():
        c.execute(sa.text("UPDATE course_members SET permissions = CAST(:p AS jsonb), role = 'teacher' WHERE role = :r"),
                  {"p": json.dumps(perms), "r": old})

    # a course without a subject gets a subject of its own (so nothing is lost)
    pos = c.execute(sa.text("SELECT coalesce(max(position), 0) FROM subjects")).scalar()
    for cid, code, name in c.execute(sa.text("SELECT id, code, name FROM courses WHERE subject_id IS NULL")).all():
        pos += 1
        sid = uuid.uuid4()
        scode = code
        while c.execute(sa.text("SELECT 1 FROM subjects WHERE code = :c"), {"c": scode}).first():
            scode = f"{code[:14]}-{secrets.token_hex(2)}"
        c.execute(sa.text("""INSERT INTO subjects (id, code, name, name_en, semester, elective, languages, icon, color,
                                                   description, position)
                             VALUES (:id, :code, :name, '', NULL, true, '[]', 'book-open', '#2747C9', '', :pos)"""),
                  {"id": sid, "code": scode[:20], "name": name[:200], "pos": pos})
        c.execute(sa.text("UPDATE courses SET subject_id = :s WHERE id = :c"), {"s": sid, "c": cid})

    # the courses of one subject → the oldest one
    refs = c.execute(sa.text("""
        SELECT tc.table_name, kcu.column_name
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu ON kcu.constraint_name = tc.constraint_name
        JOIN information_schema.constraint_column_usage ccu ON ccu.constraint_name = tc.constraint_name
        WHERE tc.constraint_type = 'FOREIGN KEY' AND ccu.table_name = 'courses' AND ccu.column_name = 'id'
    """)).all()
    groups = c.execute(sa.text("""SELECT subject_id, array_agg(id ORDER BY created_at, id) FROM courses
                                  GROUP BY subject_id HAVING count(*) > 1""")).all()
    for subject_id, ids in groups:
        keep, others = ids[0], ids[1:]
        for other in others:
            # people: one membership per person (a teacher keeps all the permissions they had)
            for uid, perms, role in c.execute(sa.text(
                    "SELECT user_id, permissions, role FROM course_members WHERE course_id = :o"), {"o": other}).all():
                mine = c.execute(sa.text("SELECT id, permissions, role FROM course_members WHERE course_id = :k AND user_id = :u"),
                                 {"k": keep, "u": uid}).first()
                if mine:
                    merged = sorted(set(mine[1] or []) | set(perms or []))
                    c.execute(sa.text("UPDATE course_members SET permissions = CAST(:p AS jsonb), role = :r WHERE id = :i"),
                              {"p": json.dumps(merged), "r": "teacher" if "teacher" in (role, mine[2]) else "student", "i": mine[0]})
                    c.execute(sa.text("DELETE FROM course_members WHERE course_id = :o AND user_id = :u"), {"o": other, "u": uid})
            for table, col in refs:
                c.execute(sa.text(f'UPDATE "{table}" SET "{col}" = :k WHERE "{col}" = :o'), {"k": keep, "o": other})
            fg = c.execute(sa.text("SELECT final_grades FROM courses WHERE id = :o"), {"o": other}).scalar() or {}
            if fg:
                c.execute(sa.text("UPDATE courses SET final_grades = CAST(:f AS jsonb) || final_grades WHERE id = :k"),
                          {"f": json.dumps(fg), "k": keep})
            c.execute(sa.text("UPDATE events SET course_id = :k WHERE course_id = :o"), {"k": keep, "o": other})
            c.execute(sa.text("DELETE FROM courses WHERE id = :o"), {"o": other})

    # every subject has its space
    for sid, code, name in c.execute(sa.text("""SELECT s.id, coalesce(s.finki_code, s.code), s.name FROM subjects s
                                                WHERE NOT EXISTS (SELECT 1 FROM courses c WHERE c.subject_id = s.id)""")).all():
        jc = secrets.token_hex(4).upper()
        c.execute(sa.text("""INSERT INTO courses (id, code, name, semester, description, join_code, join_enabled, archived,
                                                  created_at, language, grading, final_grades, reminders_enabled, reminder_hours, subject_id)
                             VALUES (:id, :code, :name, '', '', :jc, false, false, now(), 'mk', '{}', '{}', true, 24, :s)"""),
                  {"id": uuid.uuid4(), "code": code[:50], "name": name, "jc": jc, "s": sid})
    op.create_index("uq_courses_subject", "courses", ["subject_id"], unique=True)


def downgrade() -> None:
    op.drop_index("uq_courses_subject", table_name="courses")
    op.drop_column("course_members", "source")
    op.drop_column("course_members", "permissions")
