"""
Grading scheme, students' standing and the grade sheet.

  GET  /courses/{id}/grading               staff: the scheme (weights, thresholds, rules)
  PUT  /courses/{id}/grading               teacher: save it
  GET  /courses/{id}/standing              staff: every student · student: only themself
  GET  /courses/{id}/gradesheet.xlsx       staff: the grade sheet (optionally ?group=<name>)
  PUT  /courses/{id}/final-grades          teacher (професор): a student's final grade 5–10
"""
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import access
from app.core.deps import get_current_user
from app.database import get_db
from app.models.course import CourseMember
from app.models.user import User
from app.routers.assignments import gradebook_data
from app.services import gradesheet, standing

router = APIRouter(tags=["standing"])


@router.get("/courses/{course_id}/grading")
async def get_grading(course_id: uuid.UUID, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    course, _ = await access.load_course(db, user, course_id, access.COURSE_STAFF)
    return standing.scheme(course)


@router.put("/courses/{course_id}/grading")
async def set_grading(course_id: uuid.UUID, body: dict, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    course, _ = await access.load_course(db, user, course_id, access.GRADE_RULERS)   # the professor writes the rules
    try:
        course.grading = standing.validate(body)
    except (ValueError, TypeError) as e:
        raise HTTPException(status_code=422, detail=str(e))
    await db.commit()
    return standing.scheme(course)


class FinalGradeIn(BaseModel):
    user_id: uuid.UUID
    grade: Optional[int] = Field(None, ge=5, le=10)   # None clears it


@router.put("/courses/{course_id}/final-grades")
async def set_final_grade(course_id: uuid.UUID, body: FinalGradeIn, db: AsyncSession = Depends(get_db),
                          user: User = Depends(get_current_user)):
    """Only the professor enters the final grade (5–10); the standing's proposed grade is a suggestion."""
    course, _ = await access.load_course(db, user, course_id, access.GRADE_RULERS)
    m = (await db.execute(select(CourseMember).where(CourseMember.course_id == course.id, CourseMember.user_id == body.user_id,
                                                     CourseMember.role == "student"))).scalar_one_or_none()
    if m is None:
        raise HTTPException(status_code=404, detail="Student not found")
    grades = dict(course.final_grades or {})
    if body.grade is None:
        grades.pop(str(body.user_id), None)
    else:
        grades[str(body.user_id)] = {"grade": body.grade, "by": str(user.id), "at": datetime.utcnow().isoformat() + "Z"}
    course.final_grades = grades
    await db.commit()
    return {"user_id": str(body.user_id), "final_grade": body.grade}


@router.get("/courses/{course_id}/standing")
async def get_standing(course_id: uuid.UUID, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    course, role = await access.load_course(db, user, course_id)
    if role == "lab":   # a лаборант works with the labs only, not the whole course's standing
        raise HTTPException(status_code=403, detail="Course staff access required")
    st = await standing.compute(db, course, await gradebook_data(db, course.id))
    if role == "student":
        me = next((s for s in st["students"] if s["user_id"] == str(user.id)), None)
        return {"scheme": st["scheme"], "me": me}
    return st


@router.get("/courses/{course_id}/gradesheet.xlsx")
async def download_gradesheet(course_id: uuid.UUID, group: Optional[str] = None, db: AsyncSession = Depends(get_db),
                              user: User = Depends(get_current_user)):
    course, _ = await access.load_course(db, user, course_id, access.COURSE_STAFF)
    data = await gradesheet.build(db, course, group)
    name = gradesheet.file_name(course)
    return Response(content=data, media_type=gradesheet.XLSX, headers={
        "Content-Disposition": f'attachment; filename="{name}"', "X-Content-Type-Options": "nosniff"})
