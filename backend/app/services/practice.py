"""
AI practice: a whole new task for one student — the task text, starting code, model solution and tests — in a
subject and language they choose. It runs on the student's own AI key (profile → My AI key).

Tests are never trusted blindly: the AI drafts them, the platform runs them on the AI's model solution, and only
tests the solution passes are kept — with the expected output taken from what the solution really prints. A task
with too few good tests is drafted again (once). Diagrams: the AI draws the model solution from the task text and
the checks are made from the drawing (as for teachers' diagram tasks).
The task is saved for that student only (not public, not in the bank); the tutor, hints and visualizations then
work on it like on any task.
"""
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import Subject, Task, TestCase
from app.models.user import User
from app.services import agent_service, code_runner_client, diagrams, limits

PROGRAM_LANGS = {"c", "bash"}          # practice tasks there are whole programs (stdin -> stdout)
MIN_TESTS = 3


def task_kind(language: str) -> str:
    if language in ("sql", "postgresql"):
        return "query"
    if language == "web" or diagrams.is_diagram(language):
        return "function"
    return "program" if language in PROGRAM_LANGS else "function"


async def _previous_titles(db: AsyncSession, user: User, subject: Subject) -> list[str]:
    return list((await db.execute(select(Task.title).where(
        Task.generated_for == user.id, Task.subject_id == subject.id).order_by(Task.created_at.desc()).limit(30))).scalars())


async def _tests_for_code(user: User, draft: dict, language: str, kind: str, lang: str) -> list[dict]:
    """AI-drafted tests, kept only where the model solution passes; expected output = what it really prints."""
    try:
        drafts = await agent_service.suggest_tests(draft["description"], language, draft["model_solution"], [], kind, count=6)
    except agent_service.AIUnavailable:
        raise
    except Exception:
        return []
    if not drafts:
        return []
    payload = [{"type": t["type"], "test_code": t["test_code"], "stdin": t["stdin"], "expected_output": t["expected_output"]}
               for t in drafts]
    async with limits.test_run(user):
        try:
            results = await code_runner_client.run_tests(draft["model_solution"], payload, language, draft["model_solution"], lang)
        except code_runner_client.RunnerBusy:
            raise HTTPException(status_code=503, detail="Code runner is busy", headers={"Retry-After": "10"})
    keep = []
    for t, r in zip(drafts, results):
        if r.error:
            continue
        visual = language == "web" and t["test_code"].lstrip().startswith("// visual")
        if visual:
            if r.passed:
                keep.append({**t, "expected_output": ""})
            continue
        if not (r.actual_output or "").strip():
            continue
        keep.append({**t, "expected_output": r.actual_output})
    # the same expected output twice teaches nothing — keep the first
    seen, out = set(), []
    for t in keep:
        k = (t["type"], t["test_code"].strip(), t["stdin"].strip())
        if k not in seen:
            seen.add(k)
            out.append(t)
    return out


async def generate(db: AsyncSession, user: User, subject: Subject, language: str, level: str, topic: str,
                   lang: str, for_student: bool = True, previous: list[str] | None = None) -> Task:
    """for_student=False: staff make a task for their course (colloquium exercises, labs) — it goes into the bank
    (not public; the course uses it through an assignment) instead of being one student's own practice."""
    kind = task_kind(language)
    if previous is None:
        previous = await _previous_titles(db, user, subject)
    subject_name = subject.name if lang == "mk" else (subject.name_en or subject.name)
    await db.commit()  # don't hold the connection while the AI writes and the tests run
    draft, tests = None, []
    for _ in range(2):
        try:
            draft = await agent_service.practice_task(subject_name, language, kind, level, topic, previous, lang)
        except agent_service.AIUnavailable:
            raise
        except Exception:
            continue
        if diagrams.is_diagram(language):
            try:
                raw = await agent_service.diagram_draft(draft["description"], language)
            except agent_service.AIUnavailable:
                raise
            except Exception:
                continue
            d = diagrams.layout(diagrams.parse({**raw, "kind": language}, language))
            if len(d["nodes"]) < 2:
                continue
            draft["model_solution"], draft["starter_code"] = diagrams.dump(d), diagrams.empty(language)
            tests = [{"type": "diagram", "test_code": c["test_code"], "stdin": "", "expected_output": c["expected_output"]}
                     for c in diagrams.generate_checks(d, lang, methods=language == "uml")]
        else:
            if not draft["model_solution"]:
                continue
            tests = await _tests_for_code(user, draft, language, kind, lang)
        if len(tests) >= MIN_TESTS:
            break
        previous = [*previous, draft["title"]]
    if draft is None or len(tests) < MIN_TESTS:
        raise HTTPException(status_code=502, detail="Could not make a good practice task, try again")

    task = Task(title=draft["title"], description=draft["description"], starter_code=draft["starter_code"],
                model_solution=draft["model_solution"], language=language, kind="code", is_public=False,
                subject_id=subject.id, generated_for=user.id if for_student else None, created_by=user.id,
                content_lang=lang, translations={})
    db.add(task)
    await db.flush()
    hidden_from = len(tests) - max(1, len(tests) // 3)  # the last third are hidden, like in the labs
    for i, t in enumerate(tests):
        db.add(TestCase(task_id=task.id, type=t["type"], test_code=t["test_code"], stdin=t["stdin"],
                        expected_output=t["expected_output"], is_hidden=i >= hidden_from and len(tests) > MIN_TESTS, order=i))
    await db.commit()
    return task


async def generate_project(db: AsyncSession, user: User, subject: Subject, language: str, level: str, topic: str,
                           lang: str, previous: list[str]) -> Task:
    """Staff: a project task (the students hand in a zip) with a rubric; the AI's reference solution is zipped and
    kept for the staff (the "reference solution" file of the task)."""
    import io
    import re
    import zipfile
    from app.models.task import TaskFile
    subject_name = subject.name if lang == "mk" else (subject.name_en or subject.name)
    await db.commit()
    draft = None
    for _ in range(2):
        try:
            draft = await agent_service.project_task(subject_name, language, level, topic, previous, lang)
            break
        except agent_service.AIUnavailable:
            raise
        except Exception:
            continue
    if draft is None:
        raise HTTPException(status_code=502, detail="Could not make a good task, try again")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for f in draft["files"]:
            z.writestr(f["path"], f["content"])
    data = buf.getvalue()
    slug = re.sub(r"[^a-z0-9]+", "-", draft["title"].lower()).strip("-")[:40] or "project"
    task = Task(title=draft["title"], description=draft["description"], starter_code="", model_solution="",
                language=language, kind="project", is_public=False, subject_id=subject.id, created_by=user.id,
                rubric=draft["rubric"], content_lang=lang, translations={})
    db.add(task)
    await db.flush()
    db.add(TaskFile(task_id=task.id, name=f"{slug}-reference.zip", content_type="application/zip", size=len(data), data=data))
    await db.commit()
    return task
