from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.task import Task, TestCase
from app.models.user import User
from app.schemas.task import TaskCreate, TaskUpdate, TaskAdminOut, TaskListItem, TestCaseCreate, TestCaseOut
from app.core.deps import get_current_admin

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/tasks", response_model=list[TaskListItem])
async def list_tasks(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    result = await db.execute(select(Task).order_by(Task.created_at))
    return [TaskListItem.model_validate(t) for t in result.scalars().all()]


@router.post("/tasks", response_model=TaskAdminOut, status_code=201)
async def create_task(
    data: TaskCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    task = Task(
        title=data.title,
        description=data.description,
        starter_code=data.starter_code,
        model_solution=data.model_solution,
        language=data.language,
        created_by=current_user.id,
    )
    db.add(task)
    await db.flush()

    for i, tc in enumerate(data.test_cases):
        test_case = TestCase(
            task_id=task.id,
            type=tc.type,
            test_code=tc.test_code,
            stdin=tc.stdin,
            expected_output=tc.expected_output,
            is_hidden=tc.is_hidden,
            order=tc.order if tc.order else i,
        )
        db.add(test_case)

    await db.commit()

    result = await db.execute(
        select(Task).options(selectinload(Task.test_cases)).where(Task.id == task.id)
    )
    return TaskAdminOut.model_validate(result.scalar_one())


@router.get("/tasks/{task_id}", response_model=TaskAdminOut)
async def get_task(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    result = await db.execute(
        select(Task).options(selectinload(Task.test_cases)).where(Task.id == task_id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return TaskAdminOut.model_validate(task)


@router.put("/tasks/{task_id}", response_model=TaskAdminOut)
async def update_task(
    task_id: str,
    data: TaskUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    result = await db.execute(
        select(Task).options(selectinload(Task.test_cases)).where(Task.id == task_id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    for field, val in data.model_dump(exclude_none=True).items():
        setattr(task, field, val)

    await db.commit()
    await db.refresh(task)
    return TaskAdminOut.model_validate(task)


@router.delete("/tasks/{task_id}", status_code=204)
async def delete_task(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    await db.delete(task)
    await db.commit()


@router.post("/tasks/{task_id}/test-cases", response_model=TestCaseOut, status_code=201)
async def add_test_case(
    task_id: str,
    data: TestCaseCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    result = await db.execute(select(Task).where(Task.id == task_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Task not found")

    tc = TestCase(
        task_id=task_id,
        type=data.type,
        test_code=data.test_code,
        stdin=data.stdin,
        expected_output=data.expected_output,
        is_hidden=data.is_hidden,
        order=data.order,
    )
    db.add(tc)
    await db.commit()
    await db.refresh(tc)
    return TestCaseOut.model_validate(tc)


@router.delete("/tasks/{task_id}/test-cases/{tc_id}", status_code=204)
async def delete_test_case(
    task_id: str,
    tc_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    result = await db.execute(
        select(TestCase).where(TestCase.id == tc_id, TestCase.task_id == task_id)
    )
    tc = result.scalar_one_or_none()
    if not tc:
        raise HTTPException(status_code=404, detail="Test case not found")
    await db.delete(tc)
    await db.commit()
