"""
Profiles: picture, name, a few facts (staff: title, office, consultation hours, bio; students: index, programme).

Who sees what
  - staff profiles (assistants, professors, admins): everyone who is signed in
  - student profiles: the student, admins, and people who share a course with them
  - a student's index / programme / year: the student, admins, and the staff of a course they share
  - e-mail: as above, plus everyone allowed to see the profile when the person chose "show my e-mail"

Routes
  GET/PUT /profile                 my profile
  PUT/DELETE /profile/avatar       my picture (a square JPEG/PNG/WebP, max 512 KB — the browser resizes it first)
  POST /profile/password           change my password (password accounts)
  GET /users/{id}/profile          someone's profile, as I may see it
  GET /users/{id}/avatar?v=&s=     the picture (signed link, so <img> works without the login token)
"""
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy import and_, select
from sqlalchemy.orm import aliased
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.core.security import avatar_signature, avatar_url, hash_password, verify_password
from app.database import get_db
from app.models.course import Course, CourseMember
from app.models.user import User, UserProfile

router = APIRouter(tags=["profiles"])

MAX_AVATAR = 512 * 1024
_MAGIC = {b"\xff\xd8\xff": "image/jpeg", b"\x89PNG\r\n\x1a\n": "image/png"}


class ProfileIn(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    title: str = Field("", max_length=120)
    bio: str = Field("", max_length=3000)
    office: str = Field("", max_length=120)
    consultation_hours: str = Field("", max_length=300)
    website: str = Field("", max_length=300)
    index_number: str = Field("", max_length=30)
    study_program: str = Field("", max_length=200)
    study_year: Optional[int] = Field(None, ge=1, le=6)
    show_email: bool = True
    email_reminders: bool = True


class PasswordIn(BaseModel):
    current: str = Field(min_length=1, max_length=200)
    new: str = Field(min_length=8, max_length=200)


async def _profile(db: AsyncSession, user_id) -> UserProfile | None:
    return (await db.execute(select(UserProfile).where(UserProfile.user_id == user_id))).scalar_one_or_none()


def _staff(u: User) -> bool:
    return u.role != "student"


async def _relation(db: AsyncSession, viewer: User, target: User) -> tuple[bool, bool]:
    """(shares a course, viewer is staff in a course they share). Every student is in the spaces of the mandatory
    subjects, so two students who are both there only through their study plan aren't "classmates" for this — only
    when the admin or Moodle put one of them in (a real class), or a teacher is involved."""
    if viewer.id == target.id:
        return True, True
    me, them = aliased(CourseMember), aliased(CourseMember)
    rows = (await db.execute(
        select(me.role, me.source, them.role, them.source).join(them, and_(them.course_id == me.course_id, them.user_id == target.id))
        .join(Course, Course.id == me.course_id).where(me.user_id == viewer.id)
    )).all()
    shared = [r for r in rows if "teacher" in (r[0], r[2]) or not (r[1] == "plan" and r[3] == "plan")]
    return bool(shared), any(r[0] == "teacher" for r in shared)


def _out(u: User, p: UserProfile | None, *, email: bool, student_facts: bool) -> dict:
    p = p or UserProfile()
    out = {
        "id": str(u.id), "name": u.name, "role": u.role, "avatar_url": avatar_url(u.id, u.avatar_version),
        "email": u.email if email else None, "bio": p.bio or "",
    }
    if _staff(u):
        out.update({"title": p.title or "", "office": p.office or "", "consultation_hours": p.consultation_hours or "",
                    "website": p.website or ""})
    elif student_facts:
        out.update({"index_number": p.index_number or "", "study_program": p.study_program or "", "study_year": p.study_year})
    return out


@router.get("/profile")
async def my_profile(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    p = await _profile(db, user.id)
    out = _out(user, p, email=True, student_facts=True)
    out.update({"show_email": p.show_email if p else True, "email_reminders": p.email_reminders if p else True,
                "auth_provider": user.auth_provider, "email": user.email})
    return out


@router.put("/profile")
async def update_profile(body: ProfileIn, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    p = await _profile(db, user.id)
    if p is None:
        p = UserProfile(user_id=user.id)
        db.add(p)
    user.name = body.name.strip()
    p.bio, p.show_email, p.email_reminders = body.bio.strip(), body.show_email, body.email_reminders
    if _staff(user):
        p.title, p.office = body.title.strip(), body.office.strip()
        p.consultation_hours, p.website = body.consultation_hours.strip(), body.website.strip()
    else:
        p.index_number, p.study_program, p.study_year = body.index_number.strip(), body.study_program.strip(), body.study_year
    await db.commit()
    return await my_profile(db, user)


@router.put("/profile/avatar")
async def upload_avatar(file: UploadFile = File(...), db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    data = await file.read(MAX_AVATAR + 1)
    if len(data) > MAX_AVATAR:
        raise HTTPException(status_code=413, detail="Picture too large")
    kind = next((t for m, t in _MAGIC.items() if data.startswith(m)), None)
    if kind is None and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        kind = "image/webp"
    if kind is None:  # checked by content, not by the name or the type the browser claims
        raise HTTPException(status_code=422, detail="Use a JPEG, PNG or WebP picture")
    p = await _profile(db, user.id)
    if p is None:
        p = UserProfile(user_id=user.id)
        db.add(p)
    p.avatar, p.avatar_type = data, kind
    user.avatar_version = (user.avatar_version or 0) + 1
    await db.commit()
    return {"avatar_url": avatar_url(user.id, user.avatar_version)}


@router.delete("/profile/avatar", status_code=204)
async def delete_avatar(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    p = await _profile(db, user.id)
    if p is not None:
        p.avatar, p.avatar_type = None, ""
    user.avatar_version = None
    await db.commit()


@router.post("/profile/password", status_code=204)
async def change_password(body: PasswordIn, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    if user.auth_provider != "password":
        raise HTTPException(status_code=400, detail="Use Microsoft sign-in")
    if not await run_in_threadpool(verify_password, body.current, user.password_hash):
        raise HTTPException(status_code=400, detail="Current password is wrong")
    user.password_hash = await run_in_threadpool(hash_password, body.new)
    await db.commit()


@router.get("/users/{user_id}/profile")
async def user_profile(user_id: uuid.UUID, db: AsyncSession = Depends(get_db), viewer: User = Depends(get_current_user)):
    target = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if target is None:
        raise HTTPException(status_code=404, detail="User not found")
    shares, staff_of = await _relation(db, viewer, target)
    admin = viewer.role == "admin"
    if not (_staff(target) or shares or admin):
        raise HTTPException(status_code=404, detail="User not found")
    p = await _profile(db, target.id)
    sees_all = admin or staff_of
    return _out(target, p, email=sees_all or (p.show_email if p else True), student_facts=sees_all)


@router.get("/users/{user_id}/avatar")
async def avatar(user_id: uuid.UUID, v: int = Query(...), s: str = Query(...), db: AsyncSession = Depends(get_db)):
    import hmac
    if not hmac.compare_digest(s, avatar_signature(user_id, v)):
        raise HTTPException(status_code=404, detail="Not found")
    row = (await db.execute(select(UserProfile.avatar, UserProfile.avatar_type, User.avatar_version)
                            .join(User, User.id == UserProfile.user_id).where(UserProfile.user_id == user_id))).first()
    if row is None or row[0] is None or row[2] != v:
        raise HTTPException(status_code=404, detail="Not found")
    # the version is in the link, so a new picture gets a new link: cache this one for a long time
    return Response(content=row[0], media_type=row[1], headers={
        "Cache-Control": "private, max-age=604800, immutable", "X-Content-Type-Options": "nosniff"})
