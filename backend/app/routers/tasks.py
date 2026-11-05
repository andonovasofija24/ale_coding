from typing import Optional
import hashlib

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.task import Task, TestCase
from app.models.session import Session
from app.schemas.task import TaskOut, TaskListItem, TestCasePublic, TestVisualizationOut
from app.core.deps import get_current_user
from app.core import access
from app.core.language import Lang, get_language
from app.models.user import User
from pydantic import BaseModel, Field

from app.services import code_runner_client, content, grading, agent_service, exam, observability, limits
from app.config import settings
from app.services.diagrams import KINDS as diagram_kinds

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("", response_model=list[TaskListItem])
async def list_tasks(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    lang: Optional[Lang] = Depends(content.reader_language),
):
    """The practice collection: public code tasks (staff also see course-only ones), titles in the reader's language."""
    q = select(Task).where(Task.kind == "code", Task.generated_for.is_(None)).order_by(Task.created_at)
    if not access.is_staff(current_user):
        q = q.where(Task.is_public.is_(True))
    result = await db.execute(q)
    return [TaskListItem.model_validate(t).model_copy(update={"title": content.title(t, lang)}) for t in result.scalars().all()]


@router.get("/{task_id}/ai-policy")
async def task_ai_policy(task_id: str, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    """How much the AI tutor may help with this task right now (an active assignment can limit or turn it off)."""
    task = await access.require_task_access(db, current_user, task_id)
    return await exam.ai_policy(db, current_user, task)


class CheckIn(BaseModel):
    code: str = Field("", max_length=200_000)


@router.post("/{task_id}/check")
async def task_check(task_id: str, body: CheckIn, db: AsyncSession = Depends(get_db),
                     current_user: User = Depends(get_current_user)):
    """Compiler errors and warnings for the editor (the code is compiled, never run). Skipped quietly when the
    student checks too often, when the runner is busy, or when the assignment turned the checks off."""
    task = await access.require_task_access(db, current_user, task_id)
    if not await exam.editor_checks_allowed(db, current_user, task):
        return {"diagnostics": [], "skipped": True, "off": True}
    if task.language == "web" or task.language in diagram_kinds:  # no compiler: the diagram / page editor shows problems itself
        return {"diagnostics": [], "skipped": True}
    types = set((await db.execute(select(TestCase.type).where(TestCase.task_id == task.id))).scalars().all())
    kind = "program" if types == {"stdin_stdout"} else "function"
    language = task.language
    await db.commit()  # don't hold the connection while compiling
    if not await limits.allow(current_user, "check", settings.RATE_CHECKS_PER_MINUTE):
        return {"diagnostics": [], "skipped": True}
    return await code_runner_client.check(body.code, language, kind)


class TaskHintIn(BaseModel):
    code: str = Field("", max_length=200_000)


@router.post("/{task_id}/hint")
async def task_hint(task_id: str, body: TaskHintIn, db: AsyncSession = Depends(get_db),
                    current_user: User = Depends(limits.limit_ai), lang: Lang = Depends(get_language)):
    """A hint for the whole task (no tutor session needed). Under an assignment in "hints" mode these are
    counted and limited; with the AI turned off there are none."""
    task = await access.require_task_access(db, current_user, task_id)
    observability.set_context(task_id=task.id)
    policy = await exam.ai_policy(db, current_user, task)
    if policy["mode"] == "off":
        raise HTTPException(status_code=403, detail="The AI tutor is turned off for this assignment")
    if policy["mode"] == "hints" and policy["hints_left"] <= 0:
        raise HTTPException(status_code=403, detail="No hints left for this task")
    try:
        hint = await agent_service.get_hint(
            step_title=task.title, step_description=task.description, student_code=body.code,
            response_language=lang, prog_language=task.language, operation="task_hint",
        )
    except agent_service.AIUnavailable:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail="Could not get a hint") from e
    after = await exam.ai_policy(db, current_user, task)
    return {"hint": hint, "hints_left": after["hints_left"]}


@router.post("/{task_id}/improve")
async def task_improve(task_id: str, body: TaskHintIn, db: AsyncSession = Depends(get_db),
                       current_user: User = Depends(limits.limit_ai), lang: Lang = Depends(get_language)):
    """AI suggestions for making a solution better — only once it passes every test. Unlimited in practice and in
    assignments with the full tutor; limited per task in "hints" mode; none when the AI is off."""
    task = await access.require_task_access(db, current_user, task_id)
    observability.set_context(task_id=task.id)
    policy = await exam.ai_policy(db, current_user, task)
    if policy["mode"] == "off":
        raise HTTPException(status_code=403, detail="The AI tutor is turned off for this assignment")
    if policy["mode"] == "hints" and not policy["improve_left"]:
        raise HTTPException(status_code=403, detail="No improvement suggestions left for this task")
    _, results = await grading.run_task_tests(db, task, body.code, current_user)
    if not results or not all(r.passed for r in results):
        raise HTTPException(status_code=400, detail="Pass all tests first")
    try:
        text = await agent_service.improve_solution(task.title, task.description, body.code, lang, task.language)
    except agent_service.AIUnavailable:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail="Could not get suggestions") from e
    after = await exam.ai_policy(db, current_user, task)
    return {"suggestions": text, "improve_left": after["improve_left"]}


@router.get("/{task_id}", response_model=TaskOut)
async def get_task(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    lang: Optional[Lang] = Depends(content.reader_language),
):
    result = await db.execute(
        select(Task)
        .options(selectinload(Task.test_cases))
        .where(Task.id == task_id)
    )
    task = result.scalar_one_or_none()
    if not task or not await access.can_access_task(db, current_user, task):
        raise HTTPException(status_code=404, detail="Task not found")

    # Only expose non-hidden test cases to students
    visible_tests = [tc for tc in task.test_cases if not tc.is_hidden]
    out = TaskOut.model_validate(task)
    out.title, out.description = content.localized(task, lang)
    out.test_cases = [TestCasePublic.model_validate(tc) for tc in visible_tests]
    out.hidden_tests = len(task.test_cases) - len(visible_tests)
    out.generated = task.generated_for is not None
    return out


# ---------------------------------------------------------------------------
# Step-by-step visualization of a visible example test
# ---------------------------------------------------------------------------

# In-process cache: the same test in the same language is only sent to the AI once.
# The key includes a hash of everything the trace depends on, so editing the task/test invalidates it.
_VIZ_CACHE: dict[tuple, list[dict]] = {}
_VIZ_CACHE_MAX = 500


def _viz_key(task: Task, tc: TestCase, lang: str) -> tuple:
    h = hashlib.sha256(
        "\x00".join([task.language, task.description, task.model_solution, tc.type, tc.test_code, tc.stdin, tc.expected_output]).encode()
    ).hexdigest()
    return (str(tc.id), lang, h)


@router.post("/{task_id}/test-cases/{tc_id}/visualize", response_model=TestVisualizationOut)
async def visualize_test_case(
    task_id: str,
    tc_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    lang: Lang = Depends(get_language),
):
    result = await db.execute(
        select(TestCase, Task)
        .join(Task, TestCase.task_id == Task.id)
        .where(TestCase.id == tc_id, TestCase.task_id == task_id)
    )
    row = result.first()
    # Hidden tests must never be explained to students — answer exactly as if the test did not exist.
    if not row or row[0].is_hidden or not await access.can_access_task(db, current_user, row[1]):
        raise HTTPException(status_code=404, detail="Test case not found")
    tc, task = row
    observability.set_context(task_id=task.id)
    await exam.require_full_ai(db, current_user, task)

    key = _viz_key(task, tc, lang)
    frames = _VIZ_CACHE.get(key)
    if frames is None:
        await limits.ai_allowed(current_user)  # cached visualizations are free
        try:
            frames = await agent_service.visualize_test(
                task_requirements=task.description,
                model_solution=task.model_solution,
                test_type=tc.type,
                test_code=tc.test_code,
                stdin=tc.stdin,
                expected_output=tc.expected_output,
                response_language=lang,
                prog_language=task.language,
            )
        except agent_service.AIUnavailable:
            raise
        except Exception as e:
            raise HTTPException(status_code=502, detail="Could not visualize the test") from e
        if len(_VIZ_CACHE) >= _VIZ_CACHE_MAX:
            _VIZ_CACHE.pop(next(iter(_VIZ_CACHE)))
        _VIZ_CACHE[key] = frames

    return TestVisualizationOut(test_case_id=tc.id, frames=frames)
