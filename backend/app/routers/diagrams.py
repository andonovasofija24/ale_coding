"""
Diagram tasks (UML class diagrams, ER diagrams).

  POST /admin/tasks/diagram-draft     staff: AI draws the model solution from the task text (and/or a PDF / picture of
                                      the task sheet) and the tests are made from it — a draft for the teacher to check
  POST /admin/tasks/diagram-tests     staff: tests made from the model solution as it is now (no AI)
  POST /tasks/{id}/diagram/read       student: a picture / PDF of their own drawing -> the diagram in the editor
                                      (read by AI exactly as drawn; the file is kept and handed in with the diagram)
  GET  /diagram-uploads/{id}          the uploaded file (its owner)
"""
import uuid
from typing import Literal

DiagramKind = Literal["uml", "er", "usecase", "state", "activity", "component", "package", "deployment", "relational", "sequence"]

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import access
from app.core.access import get_current_staff
from app.core.deps import get_current_user
from app.database import get_db
from app.models.task import DiagramUpload
from app.models.user import User
from app.services import agent_service, diagrams, limits, observability, pdfread, uploads

router = APIRouter(tags=["diagrams"])
MAX_FILE = 15 * uploads.MB


async def _read_picture(file: UploadFile, allow_text: bool = False) -> tuple[bytes, str]:
    data = await uploads.read_limited(file, MAX_FILE)
    ctype = uploads.detect_document(data)
    if ctype in (uploads.PDF, uploads.PNG, uploads.JPEG):
        return data, ctype
    raise HTTPException(status_code=422, detail="Upload a PDF or a picture (PNG, JPG)")


def _tests(d: dict, lang: str) -> list[dict]:
    return [{"type": "diagram", "test_code": c["test_code"], "stdin": "", "expected_output": c["expected_output"],
             "is_hidden": False} for c in diagrams.generate_checks(d, lang, methods=d["kind"] == "uml")]


@router.post("/admin/tasks/diagram-draft")
async def diagram_draft(kind: DiagramKind = Form(...), description: str = Form("", max_length=50_000),
                        lang: Literal["mk", "en"] = Form("mk"), file: UploadFile | None = File(None),
                        _: User = Depends(get_current_staff)):
    extra, images = "", None
    if file is not None and file.filename:
        data, ctype = await _read_picture(file)
        if ctype == uploads.PDF:
            extra = pdfread.pdf_text(data)
            if len(extra.strip()) < 40:  # a scanned sheet: no text layer -> the AI looks at the pages
                images, extra = pdfread.images_for_ai(data, ctype), ""
        else:
            images = pdfread.images_for_ai(data, ctype)
    if not description.strip() and not extra and not images:
        raise HTTPException(status_code=422, detail="Write the task description first")
    try:
        raw = await agent_service.diagram_draft(description, kind, extra, images)
    except agent_service.AIUnavailable:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail="Could not draw the diagram") from e
    d = diagrams.layout(diagrams.parse({**raw, "kind": kind}, kind))
    if not d["nodes"]:
        raise HTTPException(status_code=502, detail="Could not draw the diagram")
    return {"model_solution": diagrams.dump(d), "tests": _tests(d, lang), "used_file": bool(extra or images)}


class DiagramTestsIn(BaseModel):
    kind: DiagramKind
    model_solution: str = Field(max_length=200_000)
    lang: Literal["mk", "en"] = "mk"


@router.post("/admin/tasks/diagram-tests")
async def diagram_tests(body: DiagramTestsIn, _: User = Depends(get_current_staff)):
    d = diagrams.parse(body.model_solution, body.kind)
    if not d["nodes"]:
        raise HTTPException(status_code=422, detail="Draw the model solution first")
    return {"tests": _tests(d, body.lang)}


@router.post("/tasks/{task_id}/diagram/read")
async def read_drawing(task_id: str, file: UploadFile = File(...), db: AsyncSession = Depends(get_db),
                       user: User = Depends(limits.limit_ai)):
    task = await access.require_task_access(db, user, task_id)
    if not diagrams.is_diagram(task.language):
        raise HTTPException(status_code=400, detail="This task is not a diagram")
    observability.set_context(task_id=task.id)
    data, ctype = await _read_picture(file)
    task_kind, task_text = task.language, task.description
    await db.commit()  # don't hold the connection while the AI reads
    try:
        raw = await agent_service.diagram_read(pdfread.images_for_ai(data, ctype), task_kind, task_text)
    except agent_service.AIUnavailable:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail="Could not read the diagram from the picture") from e
    d = diagrams.layout(diagrams.parse({**raw, "kind": task_kind}, task_kind))
    for n in d["nodes"]:  # what is graded is what the student drew: no extra accepted names from the reading
        n.pop("aliases", None)
        for a in n["attributes"]:
            a.pop("aliases", None)
    text = diagrams.dump(d)
    up = DiagramUpload(user_id=user.id, task_id=task.id, file_name=uploads.safe_name(file.filename), file_type=ctype,
                       data=data, reading=text)
    db.add(up)
    await db.commit()
    return {"upload_id": str(up.id), "file_name": up.file_name, "diagram": text,
            "nodes": len(d["nodes"]), "edges": len(d["edges"])}


@router.get("/diagram-uploads/{upload_id}")
async def get_upload(upload_id: uuid.UUID, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    up = (await db.execute(select(DiagramUpload).where(DiagramUpload.id == upload_id))).scalar_one_or_none()
    if up is None or up.user_id != user.id:
        raise HTTPException(status_code=404, detail="File not found")
    return uploads.file_response(up.data, up.file_type, up.file_name, inline=True)
