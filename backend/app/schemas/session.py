import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class SessionStepOut(BaseModel):
    id: uuid.UUID
    step_number: int
    title: str
    description: str
    step_type: str
    status: str
    agent_feedback: str
    why: str = ""
    tip: str = ""

    model_config = {"from_attributes": True}


class Alternative(BaseModel):
    title: str
    idea: str = ""


class SessionOut(BaseModel):
    id: uuid.UUID
    task_id: uuid.UUID
    status: str
    current_step: int
    current_code: str
    steps: list[SessionStepOut]
    solution_no: int = 1
    approach: str = ""
    alternatives: list[Alternative] = []
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CheckStepRequest(BaseModel):
    code: str


class CheckStepResponse(BaseModel):
    passed: bool
    feedback: str
    step_completed: bool
    all_steps_completed: bool
    next_step: Optional[SessionStepOut] = None
    alternatives: list[Alternative] = []  # when the task is finished: other ways to solve it ("write another solution")


class HintRequest(BaseModel):
    code: str


class HintResponse(BaseModel):
    hint: str


class RunTestsRequest(BaseModel):
    code: str


class TestResultOut(BaseModel):
    test_number: int
    type: str
    test_code: str
    stdin: str
    expected_output: str
    actual_output: str
    passed: bool
    error: Optional[str] = None
    hidden: bool = False  # hidden test: details are blank for students
    images: Optional[dict] = None  # web visual tests: {"actual", "expected", "viewport"} screenshots


class RunTestsResponse(BaseModel):
    results: list[TestResultOut]
    total: int
    passed: int
    failed: int


class ExplainErrorsRequest(BaseModel):
    code: str
    errors: list[str]


class ExplainErrorsResponse(BaseModel):
    explanation: str


class SessionSummary(BaseModel):
    """Compact progress info for the task list (latest session per task)."""
    task_id: uuid.UUID
    session_id: uuid.UUID
    status: str
    current_step: int
    completed_steps: int
