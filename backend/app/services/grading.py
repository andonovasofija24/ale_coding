"""Running a task's tests for a user and turning the results into what that user may see."""
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import Task, TestCase
from app.models.user import User
from app.schemas.session import TestResultOut
from app.services import code_runner_client, limits


def error_kind(error: str | None) -> str | None:
    """First line of a runner error ("COMPILE ERROR", "RUNTIME ERROR", "TIME LIMIT EXCEEDED"), without details."""
    if not error:
        return None
    return error.split("\n", 1)[0].strip() or "RUNTIME ERROR"


async def run_task_tests(db: AsyncSession, task: Task, code: str, user: User):
    """Run all tests of the task (hidden ones too) on `code`, with the per-student limits.
    Returns (test_cases, results). 404 if the task has no tests, 503 if the runner is busy."""
    test_cases = (await db.execute(
        select(TestCase).where(TestCase.task_id == task.id).order_by(TestCase.order)
    )).scalars().all()
    if not test_cases:
        raise HTTPException(status_code=404, detail="No test cases found for this task")
    payload = test_payload(test_cases)
    await db.commit()  # give the database connection back while the tests run (they can take a while under load)
    async with limits.test_run(user):
        try:
            results = await code_runner_client.run_tests(code, payload, task.language, task.model_solution or "",
                                                         task.content_lang or "mk")
        except code_runner_client.RunnerBusy:
            raise HTTPException(status_code=503, detail="Code runner is busy", headers={"Retry-After": "10"})
    return test_cases, results


def test_payload(test_cases) -> list[dict]:
    return [{"type": tc.type, "test_code": tc.test_code, "stdin": tc.stdin, "expected_output": tc.expected_output}
            for tc in test_cases]


def result_rows(test_cases, results, reveal_hidden: bool) -> list[TestResultOut]:
    """Per-test results. Hidden tests are reduced to pass/fail + the kind of failure unless `reveal_hidden`
    (staff): their input, expected output, program output and error text are not sent (a compiler or runtime
    message can quote the test)."""
    out = []
    for i, (tc, rr) in enumerate(zip(test_cases, results)):
        if tc.is_hidden and not reveal_hidden:
            out.append(TestResultOut(
                test_number=i + 1, type=tc.type, test_code="", stdin="", expected_output="", actual_output="",
                passed=rr.passed, error=error_kind(rr.error), hidden=True,
            ))
        else:
            out.append(TestResultOut(
                test_number=i + 1, type=tc.type, test_code=tc.test_code, stdin=tc.stdin,
                # visual tests (web) have no written expected output: the runner says what was needed (≥ 90%)
                expected_output=tc.expected_output or (rr.expected_output or ""), actual_output=rr.actual_output,
                passed=rr.passed, error=rr.error, hidden=tc.is_hidden, images=getattr(rr, "images", None),
            ))
    return out
