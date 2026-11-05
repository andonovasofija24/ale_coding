import asyncio
import random
import time
from dataclasses import dataclass
from typing import Optional
import httpx

from app.config import settings
from app.services import observability


class RunnerBusy(Exception):
    """Every sandbox slot stayed busy for the whole queue timeout."""


@dataclass
class RunResult:
    passed: bool
    actual_output: str
    expected_output: str
    error: Optional[str] = None
    images: Optional[dict] = None  # web visual tests: screenshots of the student's page and the model solution


async def run_tests(code: str, test_cases: list[dict], language: str = "cpp", reference: str = "",
                    lang: str = "mk") -> list[RunResult]:
    """Run all test cases in the code-runner. Recorded as a "tests" event (duration, passed/total, errors).
    `reference` = the model solution; only web tasks use it (visual comparison).
    Diagrams (UML / ER) are not code: their checks run here; `lang` = the language of their messages."""
    from app.services import diagrams  # here: diagrams imports RunResult from this module
    if diagrams.is_diagram(language):
        results = diagrams.run_checks(code, test_cases, language, "en" if lang == "en" else "mk")
        await observability.record("tests", "diagram_checks", ok=True, duration_ms=0, prog_language=language,
                                   extra={"passed": sum(r.passed for r in results), "total": len(results)})
        return results
    start = time.perf_counter()
    try:
        results = await _run(code, test_cases, language, reference if language == "web" else "")
    except Exception as e:
        await observability.record("tests", "run_tests", ok=False, duration_ms=_ms(start), prog_language=language,
                                   error=f"{type(e).__name__}: {e}", extra={"total": len(test_cases)})
        raise
    passed = sum(1 for r in results if r.passed)
    compile_errors = sum(1 for r in results if (r.error or "").startswith("COMPILE"))
    await observability.record("tests", "run_tests", ok=True, duration_ms=_ms(start), prog_language=language,
                               extra={"passed": passed, "total": len(results), "compile_errors": compile_errors})
    return results


def _ms(start: float) -> int:
    return round((time.perf_counter() - start) * 1000)


async def _run(code: str, test_cases: list[dict], language: str, reference: str = "") -> list[RunResult]:
    payload = {"code": code, "test_cases": test_cases, "language": language, "reference_code": reference}
    deadline = time.monotonic() + settings.RUNNER_BUSY_RETRY_SECONDS
    delay = 1.0
    async with httpx.AsyncClient(timeout=120.0) as client:  # Java compiles each test; allow time
        while True:
            resp = await client.post(
                f"{settings.CODE_RUNNER_URL}/run",
                json=payload,
                headers={"X-Runner-Secret": settings.CODE_RUNNER_SECRET},
            )
            if resp.status_code != 503:
                break
            # Busy (every slot taken for the runner's whole queue time): wait and try again rather than failing
            # the student; the random part keeps many waiting requests from retrying at the same moment.
            if time.monotonic() + delay > deadline:
                raise RunnerBusy()
            await asyncio.sleep(delay + random.uniform(0, delay))
            delay = min(delay * 2, 10.0)
        resp.raise_for_status()
        data = resp.json()

    results = []
    for r in data["results"]:
        results.append(RunResult(
            passed=r["passed"],
            actual_output=r["actual_output"],
            expected_output=r["expected_output"],
            error=r.get("error"),
            images=r.get("images"),
        ))
    return results


async def check(code: str, language: str, kind: str) -> dict:
    """Compiler errors / warnings for the editor (never runs the code). Empty when the runner is busy or down."""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.post(f"{settings.CODE_RUNNER_URL}/check", json={"code": code, "language": language, "kind": kind},
                                  headers={"X-Runner-Secret": settings.CODE_RUNNER_SECRET})
        if r.status_code == 200:
            return r.json()
    except httpx.HTTPError:
        pass
    return {"diagnostics": [], "skipped": True}
