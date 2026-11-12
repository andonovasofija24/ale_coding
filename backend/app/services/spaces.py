"""Every subject has one space (a `courses` row) — made automatically, never by hand — with its assignments,
points, materials and mail. Students are in the spaces of their studies: every mandatory subject and the electives
they chose ("plan" memberships, kept in step here); the admin and Moodle (LTI) can add others."""
import secrets
import uuid

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.course import Course
from app.models.task import Subject


async def ensure_space(db: AsyncSession, subject: Subject) -> Course:
    c = (await db.execute(select(Course).where(Course.subject_id == subject.id))).scalar_one_or_none()
    if c is None:
        c = Course(id=uuid.uuid4(), code=(subject.finki_code or subject.code)[:50], name=subject.name, semester="",
                   description="", join_code=secrets.token_hex(4).upper(), join_enabled=False, subject_id=subject.id)
        db.add(c)
        await db.flush()
    return c


async def ensure_all(db: AsyncSession) -> int:
    made = 0
    for s in (await db.execute(select(Subject).where(~select(Course.id).where(Course.subject_id == Subject.id).exists()))).scalars():
        await ensure_space(db, s)
        made += 1
    return made


async def space_of(db: AsyncSession, subject_id) -> Course | None:
    return (await db.execute(select(Course).where(Course.subject_id == subject_id))).scalar_one_or_none()


PLAN = """
    SELECT u.id AS user_id, c.id AS course_id
    FROM users u
    JOIN subjects s ON (s.elective = false AND s.semester IS NOT NULL)
                    OR EXISTS (SELECT 1 FROM elective_choices ec WHERE ec.user_id = u.id AND ec.subject_id = s.id)
    JOIN courses c ON c.subject_id = s.id
    WHERE u.role = 'student' {only}
"""


async def sync_students(db: AsyncSession, user_id=None) -> None:
    """Put students in the spaces of their plan, and take them out of the electives they no longer have (only the
    memberships the plan made: a student the admin or Moodle added stays)."""
    only = "AND u.id = :uid" if user_id else ""
    p = {"uid": user_id} if user_id else {}
    await db.execute(text(f"""
        INSERT INTO course_members (id, course_id, user_id, role, permissions, source, role_locked, joined_at)
        SELECT gen_random_uuid(), x.course_id, x.user_id, 'student', '[]'::jsonb, 'plan', false, now()
        FROM ({PLAN.format(only=only)}) x
        ON CONFLICT ON CONSTRAINT uq_course_member DO NOTHING"""), p)
    await db.execute(text(f"""
        DELETE FROM course_members m
        WHERE m.role = 'student' AND m.source = 'plan' {"AND m.user_id = :uid" if user_id else ""}
          AND NOT EXISTS (SELECT 1 FROM ({PLAN.format(only=only)}) x WHERE x.user_id = m.user_id AND x.course_id = m.course_id)"""), p)
