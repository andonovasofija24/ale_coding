import uuid
from datetime import datetime
from typing import Optional
from typing import Literal

from pydantic import BaseModel, Field, field_validator

LANGUAGES = ("cpp", "c", "java", "python", "javascript", "sql", "postgresql", "typescript", "php", "bash",
             "csharp", "kotlin", "prolog", "lisp", "asm", "web", "uml", "er", "usecase", "state", "activity", "component", "package", "deployment", "relational", "sequence",
             "git", "dockerfile", "yaml", "terraform")  # DevOps (the code runner's app/devops.py)


def _check_language(v):
    if v is not None and v not in LANGUAGES:
        raise ValueError(f"language must be one of {', '.join(LANGUAGES)}")
    return v


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


class TranslationIn(BaseModel):
    title: str = Field("", max_length=500)
    description: str = Field("", max_length=50_000)


class RubricItem(BaseModel):
    id: str = Field(min_length=1, max_length=40)
    title: str = Field(min_length=1, max_length=200)
    points: float = Field(ge=0, le=1000)


def _check_translations(v):
    if v is None:
        return v
    bad = [k for k in v if k not in ("mk", "en")]
    if bad:
        raise ValueError("translations: only 'mk' and 'en'")
    return v


def _check_rubric(v):
    if v is not None and len({r.id for r in v}) != len(v):
        raise ValueError("rubric: criteria ids must be unique")
    return v


class TaskCreate(BaseModel):
    title: str
    description: str
    starter_code: str = ""
    model_solution: str = ""
    language: str = "cpp"
    is_public: bool = True  # in the practice collection (False = only through course assignments)
    subject_id: Optional[uuid.UUID] = None  # the FINKI subject (предмет)
    test_cases: list[TestCaseCreate] = []
    kind: Literal["code", "document", "project", "offline"] = "code"
    content_lang: Literal["mk", "en"] = "en"
    translations: dict[str, TranslationIn] = Field(default_factory=dict)
    rubric: list[RubricItem] = Field(default_factory=list, max_length=30)

    _lang = field_validator("language")(_check_language)
    _tr = field_validator("translations")(_check_translations)
    _rb = field_validator("rubric")(_check_rubric)


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    starter_code: Optional[str] = None
    model_solution: Optional[str] = None
    language: Optional[str] = None
    is_public: Optional[bool] = None
    subject_id: Optional[str] = None  # "" = no subject
    kind: Optional[Literal["code", "document", "project", "offline"]] = None
    content_lang: Optional[Literal["mk", "en"]] = None
    translations: Optional[dict[str, TranslationIn]] = None
    rubric: Optional[list[RubricItem]] = Field(None, max_length=30)

    _lang = field_validator("language")(_check_language)
    _tr = field_validator("translations")(_check_translations)
    _rb = field_validator("rubric")(_check_rubric)


class SuggestTestsIn(BaseModel):
    """Admin: the task as it is in the form (it may not be saved yet)."""
    language: str
    description: str = Field("", max_length=50_000)
    model_solution: str = Field("", max_length=200_000)
    test_cases: list[TestCaseCreate] = Field(default_factory=list, max_length=100)
    count: int = Field(5, ge=1, le=10)

    _lang = field_validator("language")(_check_language)


class TranslateIn(BaseModel):
    title: str = Field("", max_length=500)
    description: str = Field("", max_length=50_000)
    source: Literal["mk", "en"]
    target: Literal["mk", "en"]


class TaskOut(BaseModel):
    id: uuid.UUID
    title: str
    description: str
    starter_code: str
    language: str
    kind: str = "code"
    subject_id: Optional[uuid.UUID] = None
    generated: bool = False  # an AI practice task made for this student
    created_at: datetime
    test_cases: list[TestCasePublic] = []
    hidden_tests: int = 0  # how many more tests run that the student can't see

    model_config = {"from_attributes": True}


class TaskAdminOut(TaskOut):
    model_solution: str
    is_public: bool = True
    test_cases: list[TestCaseOut] = []
    content_lang: str = "en"
    translations: dict = {}
    rubric: list = []
    reference_file: Optional[dict] = None  # {"name", "size", "content_type"} of the teacher's solution file

    model_config = {"from_attributes": True}


class TaskListItem(BaseModel):
    id: uuid.UUID
    title: str
    language: str
    kind: str = "code"
    is_public: bool = True
    subject_id: Optional[uuid.UUID] = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Test-case visualization
# ---------------------------------------------------------------------------

class VizField(BaseModel):
    name: str
    value: str


class VizStructure(BaseModel):
    name: str
    kind: str  # "stack" | "array" | "queue" | "object" | "value" | "table"
    type: str = ""
    items: list[str] = []
    highlight: list[int] = []
    fields: list[VizField] = []
    value: str = ""
    columns: list[str] = []      # table
    rows: list[list[str]] = []   # table


class VizFrame(BaseModel):
    line: int
    code: str
    explanation: str
    why: str = ""          # why this moment matters
    tip: str = ""          # an extra informative fact
    focus: str = ""        # the structure being processed right now ("" = none)
    focus_index: int = -1  # the item / row in it
    focus_field: str = ""  # the field (objects)
    structures: list[VizStructure] = []
    output: str = ""
    exception: str = ""


class TestVisualizationOut(BaseModel):
    test_case_id: uuid.UUID
    frames: list[VizFrame]


# ---------------------------------------------------------------------------
# Moodle CodeRunner XML import
# ---------------------------------------------------------------------------

class ImportQuestionPreview(BaseModel):
    index: int
    title: str
    description: str
    starter_code: str
    model_solution: str
    language: str
    coderunner_type: str
    test_cases: list[TestCaseCreate]
    warnings: list[str] = []
    duplicate: bool = False


class ImportSkipped(BaseModel):
    title: str
    reason: str
    detail: str = ""


class ImportPreviewOut(BaseModel):
    questions: list[ImportQuestionPreview]
    skipped: list[ImportSkipped]
    suggested_subject_id: Optional[uuid.UUID] = None  # by the most common language of the questions (a suggestion)


class ImportCommitIn(BaseModel):
    tasks: list[TaskCreate]
    subject_id: Optional[uuid.UUID] = None  # the subject all imported tasks go to (chosen on the import page)


class ImportCommitOut(BaseModel):
    created: int
    task_ids: list[uuid.UUID]


class RunPreviewIn(BaseModel):
    """Admin: run some code (usually the model solution) against tests that may not be saved yet."""
    language: str
    code: str
    test_cases: list[TestCaseCreate]
    reference_code: str = ""  # web: what visual tests compare with (default: `code` itself)

    _lang = field_validator("language")(_check_language)


class RunPreviewResult(BaseModel):
    actual_output: str
    error: Optional[str] = None
    passed: bool
    expected_output: str = ""
    images: Optional[dict] = None


class RunPreviewOut(BaseModel):
    results: list[RunPreviewResult]
