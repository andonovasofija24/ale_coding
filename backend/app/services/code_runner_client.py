from dataclasses import dataclass
from typing import Optional
import httpx

from app.config import settings


@dataclass
class RunResult:
    passed: bool
    actual_output: str
    expected_output: str
    error: Optional[str] = None


async def run_tests(code: str, test_cases: list[dict]) -> list[RunResult]:
    payload = {"code": code, "test_cases": test_cases}
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            f"{settings.CODE_RUNNER_URL}/run",
            json=payload,
            headers={"X-Runner-Secret": settings.CODE_RUNNER_SECRET},
        )
        resp.raise_for_status()
        data = resp.json()

    results = []
    for r in data["results"]:
        results.append(RunResult(
            passed=r["passed"],
            actual_output=r["actual_output"],
            expected_output=r["expected_output"],
            error=r.get("error"),
        ))
    return results
