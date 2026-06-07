import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class TestCaseCreate(BaseModel):
    type: str  # "code_sample" | "stdin_stdout"
    test_code: str = ""
    stdin: str = ""
    expected_output: str
    is_hidden: bool = False
    order: int = 0


class TestCaseOut(BaseModel):
    id: uuid.UUID
    type: str
    test_code: str
    stdin: str
    expected_output: str
    is_hidden: bool
    order: int

    model_config = {"from_attributes": True}


class TestCasePublic(BaseModel):
    """Test case without hidden flag details — used for student view."""
    id: uuid.UUID
    type: str
    test_code: str
    stdin: str
    expected_output: str
    order: int

    model_config = {"from_attributes": True}


class TaskCreate(BaseModel):
    title: str
    description: str
    starter_code: str = ""
    model_solution: str
    language: str = "cpp"
    test_cases: list[TestCaseCreate] = []


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    starter_code: Optional[str] = None
    model_solution: Optional[str] = None
    language: Optional[str] = None


class TaskOut(BaseModel):
    id: uuid.UUID
    title: str
    description: str
    starter_code: str
    language: str
    created_at: datetime
    test_cases: list[TestCasePublic] = []

    model_config = {"from_attributes": True}


class TaskAdminOut(TaskOut):
    model_solution: str
    test_cases: list[TestCaseOut] = []

    model_config = {"from_attributes": True}


class TaskListItem(BaseModel):
    id: uuid.UUID
    title: str
    language: str
    created_at: datetime

    model_config = {"from_attributes": True}
