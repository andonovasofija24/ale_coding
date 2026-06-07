from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.task import Task, TestCase
from app.models.session import Session, SessionStep, StepAttempt
from app.models.user import User
from app.schemas.session import (
    SessionOut, CheckStepRequest, CheckStepResponse,
    HintRequest, HintResponse, RunTestsRequest, RunTestsResponse, TestResultOut,
    ExplainErrorsRequest, ExplainErrorsResponse,
)
from app.core.deps import get_current_user
from app.services import agent_service, code_runner_client

router = APIRouter(prefix="/sessions", tags=["sessions"])


class StartSessionRequest(BaseModel):
    task_id: str
    force_new: bool = False


async def _load_session(session_id: str, user_id, db: AsyncSession) -> Session:
    result = await db.execute(
        select(Session)
        .options(selectinload(Session.steps))
        .where(Session.id == session_id, Session.user_id == user_id)
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.post("", response_model=SessionOut, status_code=201)
async def start_session(
    body: StartSessionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task_id = body.task_id

    # Load task
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # Resume existing in-progress session unless force_new requested
    if not body.force_new:
        existing = await db.execute(
            select(Session)
            .options(selectinload(Session.steps))
            .where(Session.user_id == current_user.id, Session.task_id == task_id, Session.status == "in_progress")
        )
        session = existing.scalar_one_or_none()
        if session:
            return SessionOut.model_validate(session)

    # Create new session
    session = Session(
        user_id=current_user.id,
        task_id=task_id,
        current_code=task.starter_code,
    )
    db.add(session)
    await db.flush()

    # Generate plan via agent
    steps_data = await agent_service.generate_plan(
        task_requirements=task.description,
        model_solution=task.model_solution,
        language=task.language,
    )

    for i, s in enumerate(steps_data):
        step = SessionStep(
            session_id=session.id,
            step_number=i,
            title=s.get("title", f"Step {i+1}"),
            description=s.get("description", ""),
            step_type=s.get("step_type", "correctness"),
            status="active" if i == 0 else "pending",
        )
        db.add(step)

    await db.commit()

    result2 = await db.execute(
        select(Session).options(selectinload(Session.steps)).where(Session.id == session.id)
    )
    return SessionOut.model_validate(result2.scalar_one())


@router.get("/task/{task_id}", response_model=SessionOut | None)
async def get_session_for_task(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Session)
        .options(selectinload(Session.steps))
        .where(Session.user_id == current_user.id, Session.task_id == task_id)
        .order_by(Session.created_at.desc())
    )
    session = result.scalars().first()
    if not session:
        return None
    return SessionOut.model_validate(session)


@router.get("/{session_id}", response_model=SessionOut)
async def get_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return SessionOut.model_validate(await _load_session(session_id, current_user.id, db))


@router.patch("/{session_id}/code")
async def save_code(
    session_id: str,
    body: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = await _load_session(session_id, current_user.id, db)
    session.current_code = body.get("code", session.current_code)
    await db.commit()
    return {"status": "saved"}


@router.post("/{session_id}/check-step", response_model=CheckStepResponse)
async def check_step(
    session_id: str,
    body: CheckStepRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = await _load_session(session_id, current_user.id, db)

    if session.status == "completed":
        raise HTTPException(status_code=400, detail="Session already completed")

    current_step = next((s for s in session.steps if s.step_number == session.current_step), None)
    if not current_step:
        raise HTTPException(status_code=400, detail="No active step found")

    # Load task for requirements context
    task_result = await db.execute(select(Task).where(Task.id == session.task_id))
    task = task_result.scalar_one()

    # Count prior attempts for this step
    attempts_result = await db.execute(
        select(StepAttempt).where(
            StepAttempt.session_id == session.id,
            StepAttempt.step_id == current_step.id,
        )
    )
    attempt_number = len(attempts_result.scalars().all()) + 1

    # Ask agent to evaluate
    eval_result = await agent_service.evaluate_step(
        step_title=current_step.title,
        step_description=current_step.description,
        student_code=body.code,
        task_requirements=task.description,
        attempt_number=attempt_number,
    )

    # Record attempt
    attempt = StepAttempt(
        session_id=session.id,
        step_id=current_step.id,
        code=body.code,
        passed=eval_result["passed"],
        feedback=eval_result["feedback"],
    )
    db.add(attempt)

    # Update step feedback
    current_step.agent_feedback = eval_result["feedback"]
    session.current_code = body.code

    step_completed = False
    all_steps_completed = False

    if eval_result["passed"]:
        current_step.status = "completed"
        step_completed = True

        next_step_num = session.current_step + 1
        next_step = next((s for s in session.steps if s.step_number == next_step_num), None)
        if next_step:
            next_step.status = "active"
            session.current_step = next_step_num
        else:
            session.status = "completed"
            all_steps_completed = True

    await db.commit()

    return CheckStepResponse(
        passed=eval_result["passed"],
        feedback=eval_result["feedback"],
        step_completed=step_completed,
        all_steps_completed=all_steps_completed,
    )


@router.post("/{session_id}/hint", response_model=HintResponse)
async def get_hint(
    session_id: str,
    body: HintRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = await _load_session(session_id, current_user.id, db)
    current_step = next((s for s in session.steps if s.step_number == session.current_step), None)
    if not current_step:
        raise HTTPException(status_code=400, detail="No active step")

    hint = await agent_service.get_hint(
        step_title=current_step.title,
        step_description=current_step.description,
        student_code=body.code,
    )
    return HintResponse(hint=hint)


@router.post("/{session_id}/next-step", response_model=SessionOut)
async def next_step(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = await _load_session(session_id, current_user.id, db)
    current_step = next((s for s in session.steps if s.step_number == session.current_step), None)

    if current_step and current_step.status != "completed":
        raise HTTPException(status_code=400, detail="Complete current step first")

    return SessionOut.model_validate(session)


# ---------------------------------------------------------------------------
# Run all tests (no session required)
# ---------------------------------------------------------------------------
@router.post("/run-tests/{task_id}", response_model=RunTestsResponse)
async def run_tests(
    task_id: str,
    body: RunTestsRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    tc_result = await db.execute(
        select(TestCase)
        .where(TestCase.task_id == task_id)
        .order_by(TestCase.order)
    )
    test_cases = tc_result.scalars().all()
    if not test_cases:
        raise HTTPException(status_code=404, detail="No test cases found for this task")

    tc_payloads = [
        {"type": tc.type, "test_code": tc.test_code, "stdin": tc.stdin, "expected_output": tc.expected_output}
        for tc in test_cases
    ]

    run_results = await code_runner_client.run_tests(body.code, tc_payloads)

    out = []
    for i, (tc, rr) in enumerate(zip(test_cases, run_results)):
        out.append(TestResultOut(
            test_number=i + 1,
            type=tc.type,
            test_code=tc.test_code,
            stdin=tc.stdin,
            expected_output=tc.expected_output,
            actual_output=rr.actual_output,
            passed=rr.passed,
            error=rr.error,
        ))

    passed = sum(1 for r in out if r.passed)
    return RunTestsResponse(results=out, total=len(out), passed=passed, failed=len(out) - passed)


# ---------------------------------------------------------------------------
# Explain test errors via LLM
# ---------------------------------------------------------------------------
@router.post("/run-tests/{task_id}/explain", response_model=ExplainErrorsResponse)
async def explain_errors(
    task_id: str,
    body: ExplainErrorsRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task_result = await db.execute(select(Task).where(Task.id == task_id))
    task = task_result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    explanation = await agent_service.explain_test_errors(
        student_code=body.code,
        errors=body.errors,
        task_requirements=task.description,
    )
    return ExplainErrorsResponse(explanation=explanation)
