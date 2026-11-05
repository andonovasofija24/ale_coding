import uuid
from typing import Optional
from dataclasses import asdict

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, func
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.task import Subject, Task, TaskFile, TestCase
from app.models.session import Session, SessionStep, StepAttempt
from app.models.user import User
from app.schemas.task import (
    TaskCreate, TaskUpdate, TaskAdminOut, TaskListItem, TestCaseCreate, TestCaseOut,
    ImportPreviewOut, ImportQuestionPreview, ImportSkipped, ImportCommitIn, ImportCommitOut,
    RunPreviewIn, RunPreviewOut, RunPreviewResult, SuggestTestsIn, TranslateIn,
)
from app.core.language import Lang
from app.services import agent_service, code_runner_client, content, diagrams, uploads
from app.services.coderunner_import import parse_moodle_xml, CoderunnerImportError, MAX_BYTES
from app.core.access import get_current_staff

# Task authoring (the task bank): assistants, professors and admins.
router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/tasks", response_model=list[TaskListItem])
async def list_tasks(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_staff),
    lang: Optional[Lang] = Depends(content.reader_language),
):
    result = await db.execute(select(Task).where(Task.generated_for.is_(None)).order_by(Task.created_at))  # not students' AI practice
    return [TaskListItem.model_validate(t).model_copy(update={"title": content.title(t, lang)}) for t in result.scalars().all()]


async def _subject(db: AsyncSession, subject_id):
    """A subject id that exists (or None)."""
    if not subject_id:
        return None
    from app.models.task import Subject
    try:
        sid = uuid.UUID(str(subject_id))
    except ValueError:
        raise HTTPException(status_code=422, detail="Subject not found")
    if not (await db.execute(select(Subject.id).where(Subject.id == sid))).first():
        raise HTTPException(status_code=422, detail="Subject not found")
    return sid


async def _admin_out(db: AsyncSession, task_id) -> TaskAdminOut:
    task = (await db.execute(select(Task).options(selectinload(Task.test_cases)).where(Task.id == task_id))).scalar_one()
    out = TaskAdminOut.model_validate(task)
    ref = (await db.execute(select(TaskFile.name, TaskFile.size, TaskFile.content_type).where(TaskFile.task_id == task.id))).first()
    out.reference_file = {"name": ref[0], "size": ref[1], "content_type": ref[2]} if ref else None
    return out





@router.post("/tasks", response_model=TaskAdminOut, status_code=201)
async def create_task(
    data: TaskCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_staff),
):
    task = Task(
        title=data.title,
        description=data.description,
        starter_code=data.starter_code,
        model_solution=data.model_solution,
        language=data.language,
        is_public=data.is_public and data.kind == "code",  # only code tasks are in the practice collection
        subject_id=await _subject(db, data.subject_id),
        created_by=current_user.id,
        kind=data.kind,
        content_lang=data.content_lang,
        translations={k: v.model_dump() for k, v in data.translations.items() if v.title or v.description},
        rubric=[r.model_dump() for r in data.rubric],
    )
    db.add(task)
    await db.flush()

    for i, tc in enumerate(data.test_cases):
        test_case = TestCase(
            task_id=task.id,
            type=tc.type,
            test_code=tc.test_code,
            stdin=tc.stdin,
            expected_output=tc.expected_output,
            is_hidden=tc.is_hidden,
            order=tc.order if tc.order else i,
        )
        db.add(test_case)

    await db.commit()
    return await _admin_out(db, task.id)


@router.get("/tasks/{task_id}", response_model=TaskAdminOut)
async def get_task(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_staff),
):
    result = await db.execute(select(Task.id).where(Task.id == task_id))
    if result.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return await _admin_out(db, task_id)


@router.put("/tasks/{task_id}", response_model=TaskAdminOut)
async def update_task(
    task_id: str,
    data: TaskUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_staff),
):
    result = await db.execute(
        select(Task).options(selectinload(Task.test_cases)).where(Task.id == task_id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    values = data.model_dump(exclude_none=True)
    if "subject_id" in values:
        values["subject_id"] = await _subject(db, values["subject_id"] or None)
    if "translations" in values:
        values["translations"] = {k: v for k, v in values["translations"].items() if v.get("title") or v.get("description")}
    for field, val in values.items():
        setattr(task, field, val)
    if task.kind != "code":
        task.is_public = False
    await db.commit()
    return await _admin_out(db, task.id)


@router.post("/tasks/translate")
async def translate(body: TranslateIn, _: User = Depends(get_current_staff)):
    """A draft translation (MK <-> EN) of a task's title and description, for the author to check and save."""
    if body.source == body.target:
        raise HTTPException(status_code=422, detail="Choose another language")
    if not (body.title.strip() or body.description.strip()):
        raise HTTPException(status_code=422, detail="Nothing to translate")
    try:
        return await agent_service.translate_task(body.title, body.description, body.source, body.target)
    except agent_service.AIUnavailable:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail="Could not translate") from e


@router.post("/tasks/suggest-tests")
async def suggest_tests(body: SuggestTestsIn, _: User = Depends(get_current_staff)):
    """AI drafts new tests from the description and the model solution. Each draft is run on the model solution
    right away: its expected output is what the solution really prints, and a test the solution fails is marked,
    so the author only keeps tests that are right. Nothing is saved here."""
    if not body.description.strip():
        raise HTTPException(status_code=422, detail="Write the task description first")
    kind = "program" if body.test_cases and all(t.type == "stdin_stdout" for t in body.test_cases) else "function"
    try:
        drafts = await agent_service.suggest_tests(body.description, body.language, body.model_solution,
                                                   [t.model_dump() for t in body.test_cases], kind, body.count)
    except agent_service.AIUnavailable:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail="Could not suggest tests") from e
    for d in drafts:
        d["checked"] = None  # not run (no model solution)
    if body.model_solution.strip() and drafts:
        try:
            results = await code_runner_client.run_tests(
                body.model_solution, [{k: d[k] for k in ("type", "test_code", "stdin", "expected_output")} for d in drafts],
                body.language, body.model_solution)
        except Exception:
            results = []
        for d, r in zip(drafts, results):
            visual = body.language == "web" and "visual" in d["test_code"].split("\n", 1)[0].lower()
            if r.error:
                d["checked"], d["error"] = False, r.error[:1000]
            else:
                if not visual:
                    d["expected_output"] = r.actual_output  # what the model solution really prints
                d["checked"] = True
    return {"tests": drafts}


@router.put("/tasks/{task_id}/reference")
async def upload_reference(task_id: str, file: UploadFile = File(...), db: AsyncSession = Depends(get_db),
                           _: User = Depends(get_current_staff)):
    """The teacher's own solution of a document / project task (a file), shown only to staff while grading."""
    task = (await db.execute(select(Task).where(Task.id == task_id))).scalar_one_or_none()
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    data, kind = await uploads.read_checked(file, "project" if task.kind == "project" else "document")
    ref = (await db.execute(select(TaskFile).where(TaskFile.task_id == task.id))).scalar_one_or_none()
    if ref is None:
        ref = TaskFile(task_id=task.id)
        db.add(ref)
    ref.name, ref.content_type, ref.size, ref.data = uploads.safe_name(file.filename), kind, len(data), data
    await db.commit()
    return {"name": ref.name, "size": ref.size, "content_type": ref.content_type}


@router.delete("/tasks/{task_id}/reference", status_code=204)
async def delete_reference(task_id: str, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_staff)):
    await db.execute(delete(TaskFile).where(TaskFile.task_id == task_id))
    await db.commit()


@router.get("/tasks/{task_id}/reference")
async def download_reference(task_id: str, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_staff)):
    ref = (await db.execute(select(TaskFile).where(TaskFile.task_id == task_id))).scalar_one_or_none()
    if ref is None:
        raise HTTPException(status_code=404, detail="Not found")
    return uploads.file_response(ref.data, ref.content_type, ref.name)


@router.delete("/tasks/{task_id}", status_code=204)
async def delete_task(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_staff),
):
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    # Students' sessions on this task go with it (attempts -> steps -> sessions, in FK order).
    session_ids = select(Session.id).where(Session.task_id == task.id)
    await db.execute(delete(StepAttempt).where(StepAttempt.session_id.in_(session_ids)))
    await db.execute(delete(SessionStep).where(SessionStep.session_id.in_(session_ids)))
    await db.execute(delete(Session).where(Session.task_id == task.id))
    await db.delete(task)
    await db.commit()


@router.get("/tasks/{task_id}/usage")
async def task_usage(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_staff),
):
    """How much student work a delete would remove (shown in the confirmation)."""
    row = (await db.execute(
        select(func.count(Session.id), func.count(func.distinct(Session.user_id))).where(Session.task_id == task_id)
    )).one()
    return {"sessions": row[0], "students": row[1]}


@router.post("/tasks/{task_id}/test-cases", response_model=TestCaseOut, status_code=201)
async def add_test_case(
    task_id: str,
    data: TestCaseCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_staff),
):
    result = await db.execute(select(Task).where(Task.id == task_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Task not found")

    tc = TestCase(
        task_id=task_id,
        type=data.type,
        test_code=data.test_code,
        stdin=data.stdin,
        expected_output=data.expected_output,
        is_hidden=data.is_hidden,
        order=data.order,
    )
    db.add(tc)
    await db.commit()
    await db.refresh(tc)
    return TestCaseOut.model_validate(tc)


@router.put("/tasks/{task_id}/test-cases/{tc_id}", response_model=TestCaseOut)
async def update_test_case(
    task_id: str,
    tc_id: str,
    data: TestCaseCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_staff),
):
    tc = (await db.execute(
        select(TestCase).where(TestCase.id == tc_id, TestCase.task_id == task_id)
    )).scalar_one_or_none()
    if not tc:
        raise HTTPException(status_code=404, detail="Test case not found")
    tc.type, tc.test_code, tc.stdin = data.type, data.test_code, data.stdin
    tc.expected_output, tc.is_hidden, tc.order = data.expected_output, data.is_hidden, data.order
    await db.commit()
    await db.refresh(tc)
    return TestCaseOut.model_validate(tc)


@router.delete("/tasks/{task_id}/test-cases/{tc_id}", status_code=204)
async def delete_test_case(
    task_id: str,
    tc_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_staff),
):
    result = await db.execute(
        select(TestCase).where(TestCase.id == tc_id, TestCase.task_id == task_id)
    )
    tc = result.scalar_one_or_none()
    if not tc:
        raise HTTPException(status_code=404, detail="Test case not found")
    await db.delete(tc)
    await db.commit()


@router.get("/languages")
async def installed_languages(_: User = Depends(get_current_staff)):
    """Languages the code runner can run (what is installed in its image), for the task form."""
    import httpx
    from app.config import settings
    try:
        async with httpx.AsyncClient(timeout=5) as c:
            r = await c.get(f"{settings.CODE_RUNNER_URL}/health")
        return {"languages": r.json().get("languages", []) + list(diagrams.KINDS), "runner": True}
    except Exception:
        return {"languages": list(diagrams.KINDS), "runner": False}


@router.post("/run-preview", response_model=RunPreviewOut)
async def run_preview(body: RunPreviewIn, _: User = Depends(get_current_staff)):
    """Run code (normally the model solution) on the form's tests, so expected outputs can be filled in
    from what the solution really prints, and the author sees at once if the solution doesn't pass."""
    if not body.test_cases:
        return RunPreviewOut(results=[])
    try:
        results = await code_runner_client.run_tests(
            body.code,
            [{"type": t.type, "test_code": t.test_code, "stdin": t.stdin, "expected_output": t.expected_output}
             for t in body.test_cases],
            body.language, body.reference_code or body.code,
        )
    except code_runner_client.RunnerBusy:
        raise HTTPException(status_code=503, detail="Code runner is busy", headers={"Retry-After": "10"})
    return RunPreviewOut(results=[RunPreviewResult(actual_output=r.actual_output, error=r.error, passed=r.passed,
                                                   expected_output=r.expected_output, images=r.images)
                                  for r in results])


# ---------------------------------------------------------------------------
# Import from Moodle CodeRunner (Moodle XML export)
# Two steps so the admin can review before anything is saved:
#   1. preview: parse the uploaded file, return what would be created (nothing is saved)
#   2. commit:  create the tasks the admin selected, in one transaction
# ---------------------------------------------------------------------------

_IMPORT_ERRORS = {
    "tooLarge": "Import file too large",
    "notXml": "Import file is not valid XML",
    "notMoodle": "Import file is not a Moodle XML export",
    "noQuestions": "Import file contains no questions",
}


@router.post("/import/coderunner/preview", response_model=ImportPreviewOut)
async def import_coderunner_preview(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_staff),
):
    data = await file.read(MAX_BYTES + 1)
    try:
        questions, skipped = parse_moodle_xml(data)
    except CoderunnerImportError as e:
        raise HTTPException(status_code=400, detail=_IMPORT_ERRORS[e.code])

    existing = {t.strip().lower() for t in (await db.execute(select(Task.title))).scalars().all()}
    seen: set[str] = set()
    out = []
    for q in questions:
        key = q.title.strip().lower()
        d = asdict(q)
        d["duplicate"] = key in existing or key in seen
        seen.add(key)
        out.append(ImportQuestionPreview(**d))
    return ImportPreviewOut(questions=out, skipped=[ImportSkipped(**asdict(s)) for s in skipped],
                            suggested_subject_id=await _suggested_subject(db, [q.language for q in questions]))


async def _suggested_subject(db: AsyncSession, languages: list[str]):
    """The usual subject of the most common language (C → СП, C++ → ООП, …): only a suggestion, the admin chooses."""
    from collections import Counter
    from app.data.subjects import DEFAULT_FOR
    if not languages:
        return None
    code = DEFAULT_FOR.get(Counter(languages).most_common(1)[0][0])
    return (await db.execute(select(Subject.id).where(Subject.code == code))).scalar_one_or_none() if code else None


@router.post("/import/commit", response_model=ImportCommitOut, status_code=201)
async def import_commit(
    body: ImportCommitIn,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_staff),
):
    if not body.tasks:
        raise HTTPException(status_code=400, detail="Nothing selected to import")
    if len(body.tasks) > 200:
        raise HTTPException(status_code=400, detail="Too many tasks in one import")

    subject_id = await _subject(db, body.subject_id)
    ids = []
    for data in body.tasks:
        if any(tc.type not in ("code_sample", "stdin_stdout") for tc in data.test_cases):
            raise HTTPException(status_code=400, detail="Invalid test case type")
        task = Task(
            title=data.title,
            description=data.description,
            starter_code=data.starter_code,
            model_solution=data.model_solution,
            language=data.language,
            created_by=current_user.id,
            subject_id=subject_id,
        )
        db.add(task)
        await db.flush()
        for i, tc in enumerate(data.test_cases):
            db.add(TestCase(
                task_id=task.id,
                type=tc.type,
                test_code=tc.test_code,
                stdin=tc.stdin,
                expected_output=tc.expected_output,
                is_hidden=tc.is_hidden,
                order=i,
            ))
        ids.append(task.id)

    await db.commit()  # all or nothing
    return ImportCommitOut(created=len(ids), task_ids=ids)
