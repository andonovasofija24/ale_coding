"""
Course e-mail: drafts in Macedonian and English (from a template, optionally rewritten by AI), recipients, approval.

When something worth telling happens (an assignment is published, a deadline moves, grades are published, a
colloquium is graded) a *draft* is prepared — nothing is sent until a teacher reads it and presses Send.
Each student gets the version in their group's teaching language (the English group gets English).
"""
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.comms import Email, EmailDelivery
from app.models.course import Assignment, Course, CourseGroup, CourseMember
from app.models.user import User, UserProfile

TZ = ZoneInfo("Europe/Skopje")
MK_DAYS = ["понеделник", "вторник", "среда", "четврток", "петок", "сабота", "недела"]
MK_MONTHS = ["јануари", "февруари", "март", "април", "мај", "јуни", "јули", "август", "септември", "октомври", "ноември", "декември"]


def when(dt: datetime | None, lang: str) -> str:
    if dt is None:
        return "без рок" if lang == "mk" else "no deadline"
    local = dt.replace(tzinfo=timezone.utc).astimezone(TZ)
    if lang == "mk":
        return f"{MK_DAYS[local.weekday()]}, {local.day} {MK_MONTHS[local.month - 1]} {local.year}, {local:%H:%M}"
    return local.strftime("%A, %d %B %Y, %H:%M")


def link(path: str) -> str:
    return settings.FRONTEND_URL.rstrip("/") + path


# ---------------------------------------------------------------------------
# Templates (a good first draft without AI; the teacher can edit or let AI rewrite it)
# ---------------------------------------------------------------------------

def template(kind: str, course: Course, a: Assignment | None, teacher: str) -> dict:
    c = f"{course.code} — {course.name}"
    t = a.title if a else ""
    url = link(f"/assignments/{a.id}") if a else link(f"/courses/{course.id}")
    sign_mk, sign_en = f"\n\nПоздрав,\n{teacher}", f"\n\nBest regards,\n{teacher}"
    if kind == "announcement":
        return {
            "subject_mk": f"[{course.code}] Објавена е нова активност: {t}",
            "body_mk": f"Почитувани студенти,\n\nВо предметот {c} е објавена „{t}“.\nРок: {when(a.due_at, 'mk')}.\n\n"
                       f"Задачите се достапни на: {url}{sign_mk}",
            "subject_en": f"[{course.code}] New assignment: {t}",
            "body_en": f"Dear students,\n\n“{t}” has been published in {c}.\nDeadline: {when(a.due_at, 'en')}.\n\n"
                       f"You can find the tasks at: {url}{sign_en}",
        }
    if kind == "deadline":
        return {
            "subject_mk": f"[{course.code}] Променет рок: {t}",
            "body_mk": f"Почитувани студенти,\n\nРокот за „{t}“ е променет. Нов рок: {when(a.due_at, 'mk')}.\n\n{url}{sign_mk}",
            "subject_en": f"[{course.code}] Deadline changed: {t}",
            "body_en": f"Dear students,\n\nThe deadline for “{t}” has changed. New deadline: {when(a.due_at, 'en')}.\n\n{url}{sign_en}",
        }
    if kind == "grades":
        return {
            "subject_mk": f"[{course.code}] Објавени се поените: {t}",
            "body_mk": f"Почитувани студенти,\n\nПоените и коментарите за „{t}“ се објавени. Можете да ги видите на: {url}{sign_mk}",
            "subject_en": f"[{course.code}] Grades published: {t}",
            "body_en": f"Dear students,\n\nThe points and comments for “{t}” have been published. You can see them at: {url}{sign_en}",
        }
    if kind == "gradesheet":
        return {
            "subject_mk": f"[{course.code}] Листа со оцени по „{t}“",
            "body_mk": f"Во прилог е листата со оцени за {c} по „{t}“, со статусот на секој студент "
                       f"(потпис, право на полагање, предлог оценка).\n\nПредметот: {link(f'/courses/{course.id}?tab=grades')}",
            "subject_en": f"[{course.code}] Grade sheet after “{t}”",
            "body_en": f"Attached is the grade sheet for {c} after “{t}”, with each student's standing "
                       f"(signature, exam eligibility, proposed grade).\n\nCourse: {link(f'/courses/{course.id}?tab=grades')}",
        }
    if kind == "reminder":
        return {
            "subject_mk": f"[{course.code}] Потсетник: рокот за „{t}“ е {when(a.due_at, 'mk')}",
            "body_mk": f"Здраво,\n\nУште не сте предале „{t}“ во предметот {c}.\nРок: {when(a.due_at, 'mk')}.\n\n{url}\n\n"
                       f"(Потсетниците можете да ги исклучите во вашиот профил.)",
            "subject_en": f"[{course.code}] Reminder: “{t}” is due {when(a.due_at, 'en')}",
            "body_en": f"Hello,\n\nYou have not handed in “{t}” in {c} yet.\nDeadline: {when(a.due_at, 'en')}.\n\n{url}\n\n"
                       f"(You can turn reminders off in your profile.)",
        }
    return {"subject_mk": f"[{course.code}] ", "body_mk": sign_mk.strip(), "subject_en": f"[{course.code}] ", "body_en": sign_en.strip()}


async def teacher_name(db: AsyncSession, course: Course, user: User | None) -> str:
    if user is not None:
        return user.name
    row = (await db.execute(select(User.name).join(CourseMember, CourseMember.user_id == User.id).where(
        CourseMember.course_id == course.id, CourseMember.role == "teacher").limit(1))).scalar_one_or_none()
    return row or course.name


async def draft(db: AsyncSession, course: Course, kind: str, a: Assignment | None, user: User | None,
                audience: str = "students") -> Email:
    """A new draft, or the existing unsent draft of the same kind for the same assignment (refreshed)."""
    existing = None
    if a is not None:
        existing = (await db.execute(select(Email).where(
            Email.course_id == course.id, Email.assignment_id == a.id, Email.kind == kind, Email.status == "draft"))).scalar_one_or_none()
    text = template(kind, course, a, await teacher_name(db, course, user))
    e = existing or Email(course_id=course.id, assignment_id=a.id if a else None, kind=kind, audience=audience,
                          created_by=user.id if user else None,
                          group_id=a.group_id if (a is not None and audience == "students") else None)
    for k, v in text.items():
        setattr(e, k, v)
    if existing is None:
        db.add(e)
    await db.flush()
    return e


# ---------------------------------------------------------------------------
# Recipients
# ---------------------------------------------------------------------------

async def recipients(db: AsyncSession, course: Course, audience: str, group_id=None, user_ids=None,
                     reminders: bool = False) -> list[tuple]:
    """[(user_id, address, language)]. Students get their group's teaching language (else the course's)."""
    roles = ("teacher", "assistant") if audience == "staff" else ("student",)
    q = (select(User.id, User.email, CourseGroup.language, UserProfile.email_reminders)
         .join(CourseMember, CourseMember.user_id == User.id)
         .outerjoin(CourseGroup, CourseGroup.id == CourseMember.group_id)
         .outerjoin(UserProfile, UserProfile.user_id == User.id)
         .where(CourseMember.course_id == course.id, CourseMember.role.in_(roles)))
    if group_id is not None:
        q = q.where(CourseMember.group_id == group_id)
    if user_ids is not None:
        q = q.where(User.id.in_(user_ids))
    out = []
    for uid, address, glang, wants_reminders in (await db.execute(q)).all():
        if reminders and wants_reminders is False:
            continue
        out.append((uid, address, glang or course.language or "mk"))
    return out


async def queue(db: AsyncSession, email: Email, course: Course, user_ids=None, reminders: bool = False) -> int:
    """Create the deliveries (one per recipient, in their language) and mark the e-mail as sending."""
    rec = await recipients(db, course, email.audience, email.group_id, user_ids, reminders)
    for uid, address, lang in rec:
        db.add(EmailDelivery(email_id=email.id, user_id=uid, address=address, lang=lang))
    email.status, email.recipients = "sending", len(rec)
    return len(rec)
