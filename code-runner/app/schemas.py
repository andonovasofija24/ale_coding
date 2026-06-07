from pydantic import BaseModel
from typing import Optional


class TestCasePayload(BaseModel):
    type: str  # "code_sample" | "stdin_stdout"
    test_code: str = ""
    stdin: str = ""
    expected_output: str


class RunRequest(BaseModel):
    code: str
    test_cases: list[TestCasePayload]


class TestResult(BaseModel):
    passed: bool
    actual_output: str
    expected_output: str
    error: Optional[str] = None


class RunResponse(BaseModel):
    results: list[TestResult]
