"""
Who may do what.

Accounts (users.role): student | teacher | admin. (The old "assistant" / "professor" accounts are teachers.)
    student — practises in every subject; in the subjects of their studies (all the mandatory ones and the electives
              they chose) also gets what the teachers put there: practice, labs, colloquia, their points
    teacher — uses the task bank; in a subject does what the admin allowed them (core/permissions.py)
    admin   — everything: the catalogue, people and their permissions, AI, logs, LTI

Every subject has one space (a `courses` row, never made by hand) with its assignments, points, materials and mail.
Its members (course_members) are students (from their study plan, from the admin or from Moodle) and teachers with
their permissions. Admins act as a teacher with every permission everywhere.
"""
from datetime import datetime

from fastapi import Depends, HTTPException
from sqlalchemy import select, and_, or_, exists
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import permissions as P
from app.core.deps import get_current_user
from app.models.course import Course, CourseMember, Assignment, AssignmentTask
from app.models.task import Task
from app.models.user import User
from app.services import observability

STAFF_ROLES = ("teacher", "assistant", "professor", "admin")   # accounts that use the task bank
COURSE_STAFF = ("teacher",)          # any teacher of the subject (finer checks: permissions)
COURSE_GRADERS = COURSE_STAFF
LAB_KINDS = P.LAB_KINDS
LAB_CATEGORIES = P.LAB_CATEGORIES


class Role(str):
    """The person's place in a subject's space: "teacher" or "student" — with the teacher's permissions."""
    perms: frozenset

    def __new__(cls, value: str, perms=()):
        o = super().__new__(cls, value)
        o.perms = frozenset(perms)
        return o

    def can(self, perm: str) -> bool:
        return perm in self.perms

    def can_kind(self, kind: str, action: str) -> bool:
        return P.can_kind(self.perms, kind, action)

    def any(self, *perms: str) -> bool:
        return bool(self.perms & set(perms))


def lab_may_see(role, kind: str) -> bool:
    """Students see what is open to them (checked elsewhere); a teacher sees an assignment's kind only with the
    view permission of its group (labs / colloquia & homework)."""
    return role != "teacher" or role.can_kind(kind, "view")


def is_staff(user: User) -> bool:
    return user.role in STAFF_ROLES


def is_admin(user: User) -> bool:
    return user.role == "admin"


async def get_current_staff(user: User = Depends(get_current_user)) -> User:
    """Task authors: teachers and admins."""
    if not is_staff(user):
        raise HTTPException(status_code=403, detail="Staff access required")
    return user


def require_admin(user: User) -> None:
    """Subjects, people and their permissions are managed by the administrator only."""
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Only the administrator manages courses and people")


def require_role(role, allowed, what: str = "Not allowed for your role in this course") -> None:
    """`allowed`: roles ("teacher",) or a permission ("labs.grade") / permissions (any of them)."""
    if not _ok(role, allowed):
        raise HTTPException(status_code=403, detail=what)


def require_kind(role, kind: str, action: str, what: str = "You don't have this permission in this subject") -> None:
    if role != "teacher" or not role.can_kind(kind, action):
        raise HTTPException(status_code=403, detail=what)


def _ok(role, need) -> bool:
    if need is None:
        return True
    if isinstance(need, str):
        need = (need,)
    if all(n in ("teacher", "student") for n in need):
        return role in need
    return role == "teacher" and role.any(*need)


async def get_course_creator(user: User = Depends(get_current_user)) -> User:
    require_admin(user)
    return user


async def membership(db: AsyncSession, user: User, course_id) -> CourseMember | None:
    return (await db.execute(
        select(CourseMember).where(CourseMember.course_id == course_id, CourseMember.user_id == user.id)
    )).scalar_one_or_none()


async def course_role(db: AsyncSession, user: User, course_id) -> Role | None:
    if user.role == "admin":
        return Role("teacher", P.ALL)
    m = await membership(db, user, course_id)
    if m is None:
        return None
    return Role("teacher", m.permissions or ()) if m.role == "teacher" else Role("student")


async def load_course(db: AsyncSession, user: User, course_id, roles=None) -> tuple[Course, Role]:
    """The space and the user's place in it. 404 if it doesn't exist or the user isn't in it; 403 without `roles`
    (("teacher",) or a permission / permissions — any of them)."""
    course = (await db.execute(select(Course).where(Course.id == course_id))).scalar_one_or_none()
    role = await course_role(db, user, course_id) if course else None
    if course is None or role is None:
        raise HTTPException(status_code=404, detail="Course not found")
    if not _ok(role, roles):
        raise HTTPException(status_code=403, detail="Course staff access required")
    observability.set_context(course_id=course.id)   # events of this request belong to the course (logs)
    return course, role


def assignment_open(a: Assignment, now: datetime | None = None) -> bool:
    now = now or datetime.utcnow()
    return a.published and (a.opens_at is None or a.opens_at <= now)


def visible_to_student_clause(user: User, now: datetime):
    """SQL condition: the assignment is published, open, in a course where the user is a student, and for the
    whole course or for the user's group."""
    return and_(
        Assignment.published.is_(True),
        or_(Assignment.opens_at.is_(None), Assignment.opens_at <= now),
        exists().where(
            CourseMember.course_id == Assignment.course_id,
            CourseMember.user_id == user.id,
            or_(Assignment.group_id.is_(None), Assignment.group_id == CourseMember.group_id,
                CourseMember.role == "teacher"),
        ),
    )


async def subject_staff(db: AsyncSession, user: User, subject_id, perm: str = "practice.view") -> bool:
    """The admin, or a teacher of this subject with `perm` (by default: seeing what the students practise there
    with their own AI key)."""
    if is_admin(user):
        return True
    if subject_id is None:
        return False
    m = (await db.execute(select(CourseMember).join(Course, Course.id == CourseMember.course_id).where(
        CourseMember.user_id == user.id, CourseMember.role == "teacher", Course.subject_id == subject_id))).scalars().first()
    return bool(m and perm in (m.permissions or []))


async def can_access_task(db: AsyncSession, user: User, task: Task) -> bool:
    """Staff see every task; students see public tasks and tasks of assignments open to them — for an exam only
    after they started it, and for a task with variants only the variant they were given."""
    if is_staff(user) or task.is_public or (task.generated_for is not None and task.generated_for == user.id):
        return True
    if task.subject_id is not None and await subject_staff(db, user, task.subject_id):
        return True
    from app.services import exam  # (exam imports this module)
    now = datetime.utcnow()
    rows = (await db.execute(
        select(Assignment, AssignmentTask).join(AssignmentTask, AssignmentTask.assignment_id == Assignment.id).where(
            AssignmentTask.task_id == task.id, visible_to_student_clause(user, now))
    )).all()
    for a, at in rows:
        if at.variant_group is not None:
            all_tasks = (await db.execute(select(AssignmentTask).where(AssignmentTask.assignment_id == a.id))).scalars().all()
            if at.id not in {x.id for x in exam.tasks_for_student(all_tasks, a.id, user.id)}:
                continue
        if a.exam and await exam.attempt_of(db, a, user) is None:
            continue
        return True
    return False


async def require_task_access(db: AsyncSession, user: User, task_id) -> Task:
    task = (await db.execute(select(Task).where(Task.id == task_id))).scalar_one_or_none()
    if task is None or not await can_access_task(db, user, task):
        raise HTTPException(status_code=404, detail="Task not found")
    return task
