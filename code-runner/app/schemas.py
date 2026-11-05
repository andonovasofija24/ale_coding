from pydantic import BaseModel, Field
from typing import Optional


class TestCasePayload(BaseModel):
    type: str  # "code_sample" | "stdin_stdout"
    test_code: str = Field("", max_length=50_000)
    stdin: str = Field("", max_length=1_000_000)
    expected_output: str = Field(max_length=1_000_000)


class RunRequest(BaseModel):
    code: str = Field(max_length=200_000)
    test_cases: list[TestCasePayload] = Field(max_length=100)
    language: str = "cpp"  # see app/languages.py
    reference_code: str = Field("", max_length=200_000)  # the model solution (web tasks: visual comparison)


class TestResult(BaseModel):
    passed: bool
    actual_output: str
    expected_output: str
    error: Optional[str] = None
    images: Optional[dict] = None  # web visual tests: {"actual", "expected"} screenshots (data URLs), "viewport"


class RunResponse(BaseModel):
    results: list[TestResult]


class CheckRequest(BaseModel):
    code: str = Field(max_length=200_000)
    language: str = "cpp"
    kind: str = "function"  # "program" when the student writes the whole program (tests feed stdin)


class Diagnostic(BaseModel):
    line: int
    column: int = 1
    severity: str  # "error" | "warning"
    message: str


class CheckResponse(BaseModel):
    diagnostics: list[Diagnostic]
    skipped: bool = False  # no check for this language, or the runner was busy
