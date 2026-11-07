from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.task import Task, TestCase
from app.models.session import Session, SessionStep, StepAttempt
from app.models.user import User
from app.schemas.session import (
    SessionOut, SessionStepOut, SessionSummary, CheckStepRequest, CheckStepResponse,
    HintRequest, HintResponse, RunTestsRequest, RunTestsResponse, TestResultOut,
    ExplainErrorsRequest, ExplainErrorsResponse,
)
from app.core.deps import get_current_user
from app.core.language import Lang, get_language
from app.core import access
from app.services import agent_service, code_runner_client, diagrams, exam, grading, limits, observability

router = APIRouter(prefix="/sessions", tags=["sessions"])


class StartSessionRequest(BaseModel):
    task_id: str
    force_new: bool = False
    # What the student already has in the editor. A new session starts from this instead of the
    # starter code, so code typed before pressing "Start session" is not lost.
    code: str | None = None
    # "Write another solution": the title of one of the alternatives offered when the previous solution was finished.
    approach: str | None = None


# No fixed number of steps: the tutor decides when the task is done. This is only a safety net so a session
# can't go on forever if the agent keeps finding "one more thing".
MAX_STEPS = 100
MAX_SOLUTIONS = 5  # one task, at most this many different solutions (sessions) per student


def _make_step(session_id, step_number: int, data: dict) -> SessionStep:
    return SessionStep(
        session_id=session_id,
        step_number=step_number,
        title=data["title"] or f"Step {step_number + 1}",
        description=data["description"],
        step_type=data["step_type"],
        status="active",
        why=data.get("why", ""),
        tip=data.get("tip", ""),
    )


def _clip(s: str, n: int = 400) -> str:
    s = (s or "").strip()
    return s if len(s) <= n else s[:n] + " …"


async def _run_tests_report(task: Task, code: str, db: AsyncSession) -> tuple[str | None, bool | None]:
    """Really compile + run all of the task's tests on `code`.

    Returns (report for the agent, all_passed). Hidden tests are reported only by failure kind, so the agent
    cannot leak their contents to the student. Returns (None, None) if the runner is unavailable —
    step generation then falls back to judging the code alone instead of failing.
    """
    tcs = (await db.execute(
        select(TestCase).where(TestCase.task_id == task.id).order_by(TestCase.order)
    )).scalars().all()
    if not tcs:
        return None, None
    try:
        results = await code_runner_client.run_tests(
            code,
            [{"type": t.type, "test_code": t.test_code, "stdin": t.stdin, "expected_output": t.expected_output} for t in tcs],
            task.language, task.model_solution or "", task.content_lang or "mk",
        )
    except Exception:
        return None, None

    passed = sum(1 for r in results if r.passed)
    lines = [f"{passed}/{len(results)} tests passed."]
    compile_error_shown = False
    for i, (tc, r) in enumerate(zip(tcs, results), start=1):
        vis = "hidden" if tc.is_hidden else "visible"
        if r.passed:
            lines.append(f"Test {i} ({vis}): PASSED")
            continue
        err = r.error or ""
        kind = ("compile error" if err.startswith("COMPILE") else
                "time limit exceeded" if "TIME LIMIT" in err else
                "runtime error" if err else "wrong output")
        if kind == "compile error" and not compile_error_shown:
            lines.append(f"Compiler output:\n{_clip(err, 800)}")
            compile_error_shown = True
        if tc.is_hidden:
            lines.append(f"Test {i} (hidden): FAILED — {kind}")
        else:
            what = tc.test_code if tc.type == "code_sample" else f"stdin: {tc.stdin}"
            lines.append(
                f"Test {i} (visible): FAILED — {kind}\n  test: {_clip(what, 300)}\n"
                f"  expected: {_clip(tc.expected_output, 200)}\n  got: {_clip(r.actual_output, 200)}"
            )
    return "\n".join(lines), passed == len(results)


async def _task_kind(task: Task, db: AsyncSession) -> str:
    """'query' for SQL; 'program' if the student writes a whole program (all tests are stdin/stdout); else 'function'."""
    if task.language in ("sql", "postgresql"):
        return "query"
    types = set((await db.execute(select(TestCase.type).where(TestCase.task_id == task.id))).scalars().all())
    return "program" if types == {"stdin_stdout"} else "function"


async def _next_step_or_502(
    task: Task, code: str, completed_titles: list[str], lang: Lang, test_report: str | None = None,
    db: AsyncSession | None = None, approach: str = "", previous_approaches: list[str] | None = None,
) -> dict:
    """Ask the agent for the next step. On failure nothing is committed, so the student can simply retry."""
    kind = await _task_kind(task, db) if db is not None else "function"
    try:
        return await agent_service.generate_next_step(
            task_requirements=task.description,
            model_solution=task.model_solution,
            student_code=code,
            completed_steps=completed_titles,
            language=task.language,
            response_language=lang,
            test_report=test_report,
            task_kind=kind,
            approach=approach,
            previous_approaches=previous_approaches,
        )
    except agent_service.AIUnavailable:
        raise
    except Exception as e:  # OpenAI/network error or unparseable answer
        raise HTTPException(status_code=502, detail="Could not generate the next step") from e


async def _finished_solutions(db: AsyncSession, user_id, task_id) -> list[Session]:
    return (await db.execute(select(Session).where(
        Session.user_id == user_id, Session.task_id == task_id, Session.status == "completed",
    ).order_by(Session.updated_at))).scalars().all()


def _approach_names(done: list[Session]) -> list[str]:
    return [s.approach or "the first solution (the student's own approach)" for s in done]


async def _load_session(session_id: str, user_id, db: AsyncSession) -> Session:
    result = await db.execute(
        select(Session)
        .options(selectinload(Session.steps))
        .where(Session.id == session_id, Session.user_id == user_id)
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    observability.set_context(session_id=session.id, task_id=session.task_id)
    return session


@router.post("", response_model=SessionOut, status_code=201)
async def start_session(
    body: StartSessionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    lang: Lang = Depends(get_language),
):
    observability.set_context(task_id=body.task_id)
    task_id = body.task_id

    task = await access.require_task_access(db, current_user, task_id)
    if task.kind != "code":
        raise HTTPException(status_code=400, detail="The step-by-step tutor is for programming tasks")

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

    # A new session asks the AI for the first step — not allowed while an assignment turns the tutor off.
    await exam.require_full_ai(db, current_user, task)
    await limits.ai_allowed(current_user)

    # "Write another solution": one of the ways offered when the last solution was finished, from the starter code
    approach, previous = "", None
    done = await _finished_solutions(db, current_user.id, task.id)
    if body.approach:
        offered = next((a for s in reversed(done) for a in (s.alternatives or []) if a.get("title") == body.approach), None)
        if offered is None:
            raise HTTPException(status_code=400, detail="This way of solving the task was not offered")
        if len(done) >= MAX_SOLUTIONS:
            raise HTTPException(status_code=400, detail="At most 5 solutions of one task")
        approach = f"{offered['title']}: {offered.get('idea', '')}".strip(": ")
        previous = _approach_names(done)

    # Create new session
    session = Session(
        user_id=current_user.id,
        task_id=task_id,
        current_code=task.starter_code if approach else (body.code if body.code and body.code.strip() else task.starter_code),
        solution_no=len(done) + 1 if approach else 1,
        approach=approach,
        alternatives=[],
    )
    db.add(session)
    await db.flush()

    # Generate ONLY the first step, based on the starter code.
    # Further steps are generated one at a time in check_step, based on the student's code.
    next_data = await _next_step_or_502(task, session.current_code, [], lang, db=db, approach=approach,
                                        previous_approaches=previous)
    if next_data["done"]:
        # Starter code already satisfies the task (unusual) — nothing to guide.
        session.status = "completed"
    else:
        db.add(_make_step(session.id, 0, next_data))

    await db.commit()
    observability.set_context(session_id=session.id)
    await observability.activity("session_start", solution_no=session.solution_no, approach=approach or None)

    result2 = await db.execute(
        select(Session).options(selectinload(Session.steps)).where(Session.id == session.id)
    )
    return SessionOut.model_validate(result2.scalar_one())


@router.get("/overview")
async def my_overview(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user),
                      lang: Lang = Depends(get_language)):
    """The home page's console: where the person stopped (the last task in progress) and how much they have done."""
    from app.services import content
    rows = (await db.execute(select(Session, Task).join(Task, Task.id == Session.task_id)
                             .options(selectinload(Session.steps)).where(Session.user_id == current_user.id)
                             .order_by(Session.updated_at.desc()))).all()
    latest: dict = {}
    for sess, task in rows:
        latest.setdefault(task.id, (sess, task))
    done = sum(1 for sess, _ in latest.values() if sess.status == "completed")
    going = [(sess, task) for sess, task in latest.values() if sess.status != "completed"]
    nxt = None
    if going:
        sess, task = going[0]  # rows are newest first
        nxt = {"task_id": str(task.id), "title": content.title(task, lang), "language": task.language,
               "completed_steps": sum(1 for st in sess.steps if st.status == "completed"), "total_steps": len(sess.steps),
               "updated_at": sess.updated_at.isoformat() + "Z"}
    return {"continue": nxt, "completed": done, "in_progress": len(going)}


@router.get("/mine", response_model=list[SessionSummary])
async def my_sessions(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Latest session per task for the current user — used to show progress on the task list.
    Declared before "/{session_id}" so "mine" is not taken for a session id."""
    result = await db.execute(
        select(Session)
        .options(selectinload(Session.steps))
        .where(Session.user_id == current_user.id)
        .order_by(Session.created_at.desc())
    )
    latest: dict = {}
    for s in result.scalars().all():
        latest.setdefault(s.task_id, s)
    return [
        SessionSummary(
            task_id=s.task_id,
            session_id=s.id,
            status=s.status,
            current_step=s.current_step,
            completed_steps=sum(1 for st in s.steps if st.status == "completed"),
        )
        for s in latest.values()
    ]


@router.get("/task/{task_id}", response_model=SessionOut | None)
async def get_session_for_task(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    observability.set_context(task_id=task_id)
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
    current_user: User = Depends(limits.limit_ai),
    lang: Lang = Depends(get_language),
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
    await exam.require_full_ai(db, current_user, task)

    # Count prior attempts for this step
    attempts_result = await db.execute(
        select(StepAttempt).where(
            StepAttempt.session_id == session.id,
            StepAttempt.step_id == current_step.id,
        )
    )
    attempt_number = len(attempts_result.scalars().all()) + 1

    # Ask agent to evaluate
    try:
        eval_result = await agent_service.evaluate_step(
            step_title=current_step.title,
            step_description=current_step.description,
            student_code=body.code,
            task_requirements=task.description,
            attempt_number=attempt_number,
            response_language=lang,
            prog_language=task.language,
        )
    except agent_service.AIUnavailable:
        raise
    except Exception as e:  # provider/network error: nothing is saved, the student can simply retry
        raise HTTPException(status_code=502, detail="Could not check the step") from e

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
    new_step: SessionStep | None = None

    if eval_result["passed"]:
        current_step.status = "completed"
        step_completed = True
        next_step_num = session.current_step + 1

        # Sessions created before adaptive steps already have their pending steps stored.
        legacy_next = next((s for s in session.steps if s.step_number == next_step_num), None)
        if legacy_next:
            legacy_next.status = "active"
            session.current_step = next_step_num
            new_step = legacy_next
        elif next_step_num >= MAX_STEPS:
            session.status = "completed"
            all_steps_completed = True
        else:
            # Ask the agent for the single next step, based on the code the student has now.
            completed_titles = [s.title for s in session.steps if s.status == "completed"]
            # Ground the decision in reality: run all tests on the student's code first.
            report, all_passed = await _run_tests_report(task, body.code, db)
            previous = _approach_names([x for x in await _finished_solutions(db, current_user.id, task.id)
                                        if x.id != session.id]) if session.approach else None
            next_data = await _next_step_or_502(task, body.code, completed_titles, lang, report, db=db,
                                                approach=session.approach, previous_approaches=previous)
            # Safety net: when every test passes, the task is functionally solved — no more "correctness" steps.
            # (Not for "another solution": there the tests pass already with the old idea; the tutor judges the approach.)
            if all_passed and not next_data["done"] and next_data["step_type"] == "correctness" and not session.approach:
                next_data["done"] = True
            if next_data["done"]:
                session.status = "completed"
                all_steps_completed = True
            else:
                new_step = _make_step(session.id, next_step_num, next_data)
                db.add(new_step)
                session.current_step = next_step_num

    if all_steps_completed:
        # Finished: are there other, really different ways to solve it? (offered as "write another solution")
        done = [x for x in await _finished_solutions(db, current_user.id, task.id) if x.id != session.id]
        approaches = _approach_names([*done, session])
        written = len(done) + 1
        session.alternatives = await agent_service.alternative_solutions(
            task.description, task.model_solution, body.code, task.language, approaches, written, lang,
        ) if written < MAX_SOLUTIONS else []

    await db.commit()
    await observability.activity("step_check", ok=bool(eval_result["passed"]), step=current_step.step_number + 1,
                                 completed=all_steps_completed or None)
    if all_steps_completed:
        await observability.activity("task_completed", solution_no=session.solution_no)

    return CheckStepResponse(
        alternatives=session.alternatives or [],
        passed=eval_result["passed"],
        feedback=eval_result["feedback"],
        step_completed=step_completed,
        all_steps_completed=all_steps_completed,
        next_step=SessionStepOut.model_validate(new_step) if new_step else None,
    )


@router.post("/{session_id}/hint", response_model=HintResponse)
async def get_hint(
    session_id: str,
    body: HintRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(limits.limit_ai),
    lang: Lang = Depends(get_language),
):
    session = await _load_session(session_id, current_user.id, db)
    current_step = next((s for s in session.steps if s.step_number == session.current_step), None)
    if not current_step:
        raise HTTPException(status_code=400, detail="No active step")

    task = (await db.execute(select(Task).where(Task.id == session.task_id))).scalar_one()
    await exam.require_full_ai(db, current_user, task)
    hint = await agent_service.get_hint(
        step_title=current_step.title,
        step_description=current_step.description,
        student_code=body.code,
        response_language=lang,
        prog_language=task.language,
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
    observability.set_context(task_id=task_id)
    task = await access.require_task_access(db, current_user, task_id)
    test_cases, run_results = await grading.run_task_tests(db, task, body.code, current_user)
    out = grading.result_rows(test_cases, run_results, reveal_hidden=access.is_staff(current_user))
    passed = sum(1 for r in out if r.passed)
    return RunTestsResponse(results=out, total=len(out), passed=passed, failed=len(out) - passed)


# ---------------------------------------------------------------------------
# Run the program with the student's own input (cin / input() / Scanner…), no tests
# ---------------------------------------------------------------------------
class FreeRunRequest(BaseModel):
    code: str = Field(max_length=200_000)
    stdin: str = Field("", max_length=100_000)


NO_FREE_RUN = {"web", "sql", "postgresql"}


@router.post("/run/{task_id}")
async def free_run(task_id: str, body: FreeRunRequest, db: AsyncSession = Depends(get_db),
                   current_user: User = Depends(get_current_user)):
    """The whole program is run once with the input the student typed; its output (or the error) comes back.
    Counted with the test runs (same per-minute limit). Not for web pages, SQL or diagrams."""
    observability.set_context(task_id=task_id)
    task = await access.require_task_access(db, current_user, task_id)
    if task.language in NO_FREE_RUN or diagrams.is_diagram(task.language):
        raise HTTPException(status_code=400, detail="This task can't be run with your own input")
    language = task.language
    await db.commit()
    async with limits.test_run(current_user):
        try:
            results = await code_runner_client.run_tests(
                body.code, [{"type": "stdin_stdout", "test_code": "", "stdin": body.stdin, "expected_output": ""}], language)
        except code_runner_client.RunnerBusy:
            raise HTTPException(status_code=503, detail="Code runner is busy", headers={"Retry-After": "10"})
    r = results[0]
    return {"output": r.actual_output or "", "error": r.error or None}


# ---------------------------------------------------------------------------
# Explain test errors via LLM
# ---------------------------------------------------------------------------
@router.post("/run-tests/{task_id}/explain", response_model=ExplainErrorsResponse)
async def explain_errors(
    task_id: str,
    body: ExplainErrorsRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(limits.limit_ai),
    lang: Lang = Depends(get_language),
):
    observability.set_context(task_id=task_id)
    task = await access.require_task_access(db, current_user, task_id)
    await exam.require_full_ai(db, current_user, task)

    explanation = await agent_service.explain_test_errors(
        student_code=body.code,
        errors=body.errors,
        task_requirements=task.description,
        response_language=lang,
        prog_language=task.language,
    )
    return ExplainErrorsResponse(explanation=explanation)
