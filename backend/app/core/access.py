"""
Who may do what.

Platform roles (users.role):
    student    — learns; sees public tasks and the assignments of courses they are enrolled in
    assistant  — also authors tasks; manages the courses where they are staff
    professor  — also creates courses
    admin      — everything, including AI settings, monitoring and user roles

Course roles (course_members.role): teacher | assistant | lab | student. Admins act as a teacher in every course.
    The admin alone makes courses and puts people in them (with their role); there is no joining with a code.
    teacher (професор) — everything in the course: also the grading rules and the final grades (5–10), seeing the
                         points of the labs and the colloquia
    assistant          — makes and edits the assignments (mainly the labs, also colloquia / exams and homework), sets
                         their type, reviews solutions, comments, enters points and attendance, publishes the points;
                         sees the gradebook. No grading rules, no final grades.
    lab (лаборант)     — the labs (and practice) only: makes and edits them when needed and sets their type (lab or
                         practice), looks at the submissions, enters points (with the grading tutor's help) and
                         attendance, comments, publishes the lab points. Nothing else in the course.
    student            — practises in every subject; solves the labs and everything else only in the courses they
                         are enrolled in
"""
from datetime import datetime

from fastapi import Depends, HTTPException
from sqlalchemy import select, and_, or_, exists
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.models.course import Course, CourseMember, Assignment, AssignmentTask
from app.models.task import Task
from app.models.user import User
from app.services import observability

STAFF_ROLES = ("assistant", "professor", "admin")
COURSE_CREATORS = ("admin",)
COURSE_STAFF = ("teacher", "assistant")            # the whole course: people, gradebook, mail, materials, delete
COURSE_GRADERS = ("teacher", "assistant", "lab")   # assignments they may see (a лаборант only labs / practice)
ASSIGNMENT_AUTHORS = COURSE_GRADERS                # make and edit assignments (a лаборант only labs / practice)
GRADE_SETTERS = COURSE_GRADERS                     # points, attendance, comments, publishing the points
GRADE_RULERS = ("teacher",)                        # the grading rules and the final grades
LAB_KINDS = ("lab", "practice")                    # what a лаборант sees and makes
LAB_CATEGORIES = (None, "labs", "none")           # where a лаборант's assignment may count


def lab_may_see(role: str, kind: str) -> bool:
    return role != "lab" or kind in LAB_KINDS


def is_staff(user: User) -> bool:
    return user.role in STAFF_ROLES


async def get_current_staff(user: User = Depends(get_current_user)) -> User:
    """Task authors: assistants, professors, admins."""
    if not is_staff(user):
        raise HTTPException(status_code=403, detail="Staff access required")
    return user


def require_admin(user: User) -> None:
    """Courses and the people in them are managed by the administrator only."""
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Only the administrator manages courses and people")


def require_role(role: str, allowed: tuple[str, ...], what: str = "Not allowed for your role in this course") -> None:
    if role not in allowed:
        raise HTTPException(status_code=403, detail=what)


async def get_course_creator(user: User = Depends(get_current_user)) -> User:
    require_admin(user)
    return user


async def membership(db: AsyncSession, user: User, course_id) -> CourseMember | None:
    return (await db.execute(
        select(CourseMember).where(CourseMember.course_id == course_id, CourseMember.user_id == user.id)
    )).scalar_one_or_none()


async def course_role(db: AsyncSession, user: User, course_id) -> str | None:
    if user.role == "admin":
        return "teacher"
    m = await membership(db, user, course_id)
    return m.role if m else None


async def load_course(db: AsyncSession, user: User, course_id, roles: tuple[str, ...] | None = None) -> tuple[Course, str]:
    """The course and the user's role in it. 404 if it doesn't exist or the user isn't in it; 403 if the role
    is not one of `roles`."""
    course = (await db.execute(select(Course).where(Course.id == course_id))).scalar_one_or_none()
    role = await course_role(db, user, course_id) if course else None
    if course is None or role is None:
        raise HTTPException(status_code=404, detail="Course not found")
    if roles is not None and role not in roles:
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
                CourseMember.role.in_(COURSE_GRADERS)),
        ),
    )


async def subject_staff(db: AsyncSession, user: User, subject_id) -> bool:
    """Platform staff, or the professor / an assistant / a лаборант of a course of this subject: they see everything
    in the subject — also what the students practise there with their own AI key."""
    if is_staff(user):
        return True
    if subject_id is None:
        return False
    return (await db.execute(select(CourseMember.id).join(Course, Course.id == CourseMember.course_id).where(
        CourseMember.user_id == user.id, CourseMember.role.in_(COURSE_GRADERS), Course.subject_id == subject_id))).first() is not None


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
