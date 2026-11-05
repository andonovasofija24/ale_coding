"""
Course materials (lectures, exercises, other): PDFs and presentations. Presentations are also turned into a PDF so
they open in the browser.

  GET    /courses/{id}/materials          members (students: only published)
  POST   /courses/{id}/materials          staff: upload (multipart: file, title, section, week, published)
  PATCH  /materials/{id}                  staff: title, section, week, order, published
  DELETE /materials/{id}                  staff
  GET    /materials/{id}/file             the original file (download)
  GET    /materials/{id}/view             the PDF to show in the browser
"""
import uuid
from datetime import timezone
from typing import Literal, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import access
from app.core.deps import get_current_user
from app.database import get_db
from app.models.comms import MATERIAL_SECTIONS, CourseMaterial, MaterialFile
from app.models.user import User
from app.services import materials, uploads

router = APIRouter(tags=["materials"])


class MaterialPatch(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=300)
    section: Optional[Literal["lecture", "exercise", "other"]] = None
    week: Optional[int] = Field(None, ge=0, le=30)
    position: Optional[int] = Field(None, ge=0, le=10_000)
    published: Optional[bool] = None


def _out(m: CourseMaterial) -> dict:
    return {"id": str(m.id), "section": m.section, "title": m.title, "week": m.week, "position": m.position,
            "published": m.published, "file_name": m.file_name, "file_type": m.file_type, "file_size": m.file_size,
            "has_preview": m.has_preview, "created_at": m.created_at.replace(tzinfo=timezone.utc).isoformat()}


async def _material(db: AsyncSession, user: User, material_id, staff_only: bool = False) -> tuple[CourseMaterial, str]:
    m = (await db.execute(select(CourseMaterial).where(CourseMaterial.id == material_id))).scalar_one_or_none()
    if m is None:
        raise HTTPException(status_code=404, detail="Material not found")
    _, role = await access.load_course(db, user, m.course_id, access.COURSE_STAFF if staff_only else None)
    if role not in access.COURSE_STAFF and not m.published:
        raise HTTPException(status_code=404, detail="Material not found")
    return m, role


@router.get("/courses/{course_id}/materials")
async def list_materials(course_id: uuid.UUID, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    _, role = await access.load_course(db, user, course_id)
    q = select(CourseMaterial).where(CourseMaterial.course_id == course_id)
    if role not in access.COURSE_STAFF:
        q = q.where(CourseMaterial.published.is_(True))
    rows = (await db.execute(q.order_by(CourseMaterial.week.is_(None), CourseMaterial.week, CourseMaterial.position,
                                        CourseMaterial.created_at))).scalars().all()
    return {"can_convert": materials.soffice() is not None, "materials": [_out(m) for m in rows]}


@router.post("/courses/{course_id}/materials", status_code=201)
async def upload_material(course_id: uuid.UUID, file: UploadFile = File(...), title: str = Form(..., min_length=1, max_length=300),
                          section: str = Form("lecture"), week: Optional[int] = Form(None), published: bool = Form(True),
                          db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    await access.load_course(db, user, course_id, access.COURSE_STAFF)
    if section not in MATERIAL_SECTIONS:
        raise HTTPException(status_code=422, detail="Unknown section")
    if week is not None and not 0 <= week <= 30:
        raise HTTPException(status_code=422, detail="Week out of range")
    data, ctype = await materials.read_material(file)
    name = uploads.safe_name(file.filename)
    preview = None if ctype == uploads.PDF else await materials.to_pdf(data, name)
    pos = (await db.execute(select(func.coalesce(func.max(CourseMaterial.position), -1)).where(
        CourseMaterial.course_id == course_id))).scalar_one() + 1
    m = CourseMaterial(course_id=course_id, section=section, title=title.strip(), week=week, position=pos,
                       published=published, file_name=name, file_type=ctype, file_size=len(data),
                       has_preview=ctype == uploads.PDF or preview is not None, created_by=user.id)
    db.add(m)
    await db.flush()
    db.add(MaterialFile(material_id=m.id, data=data, preview=preview))
    await db.commit()
    return _out(m)


@router.patch("/materials/{material_id}")
async def update_material(material_id: uuid.UUID, body: MaterialPatch, db: AsyncSession = Depends(get_db),
                          user: User = Depends(get_current_user)):
    m, _ = await _material(db, user, material_id, staff_only=True)
    for k, v in body.model_dump(exclude_unset=True).items():
        if k == "title" and v is not None:
            v = v.strip()
        setattr(m, k, v)
    await db.commit()
    return _out(m)


@router.delete("/materials/{material_id}", status_code=204)
async def delete_material(material_id: uuid.UUID, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    m, _ = await _material(db, user, material_id, staff_only=True)
    await db.delete(m)
    await db.commit()


@router.get("/materials/{material_id}/file")
async def material_file(material_id: uuid.UUID, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    m, _ = await _material(db, user, material_id)
    data = (await db.execute(select(MaterialFile.data).where(MaterialFile.material_id == m.id))).scalar_one()
    return uploads.file_response(data, m.file_type, m.file_name)


@router.get("/materials/{material_id}/view")
async def material_view(material_id: uuid.UUID, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    m, _ = await _material(db, user, material_id)
    row = (await db.execute(select(MaterialFile.data, MaterialFile.preview).where(MaterialFile.material_id == m.id))).one()
    pdf = row[0] if m.file_type == uploads.PDF else row[1]
    if pdf is None:
        raise HTTPException(status_code=404, detail="No preview for this file")
    return uploads.file_response(pdf, uploads.PDF, m.file_name.rsplit(".", 1)[0] + ".pdf", inline=True)
