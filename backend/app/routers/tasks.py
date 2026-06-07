from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.task import Task, TestCase
from app.models.session import Session
from app.schemas.task import TaskOut, TaskListItem, TestCasePublic
from app.core.deps import get_current_user
from app.models.user import User

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("", response_model=list[TaskListItem])
async def list_tasks(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Task).order_by(Task.created_at))
    return [TaskListItem.model_validate(t) for t in result.scalars().all()]


@router.get("/{task_id}", response_model=TaskOut)
async def get_task(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Task)
        .options(selectinload(Task.test_cases))
        .where(Task.id == task_id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # Only expose non-hidden test cases to students
    visible_tests = [tc for tc in task.test_cases if not tc.is_hidden]
    out = TaskOut.model_validate(task)
    out.test_cases = [TestCasePublic.model_validate(tc) for tc in visible_tests]
    return out
