"""
A student's electives: they choose once which electives they practise and in which semester; after they confirm
the choice, a change is a request to the admin — always one elective out and one in (the same one = another
semester), never one without the other.

  GET    /me/electives                         my plan: confirmed?, my electives, my requests
  POST   /me/electives                         add / move an elective (only while choosing)
  DELETE /me/electives/{subject_id}            take one out (only while choosing)
  POST   /me/electives/confirm                 confirm the choice (from now on: requests)
  POST   /me/elective-requests                 a change: {remove_subject_id, add_subject_id, add_semester, reason}
  DELETE /me/elective-requests/{id}            cancel my pending request
  GET    /admin/elective-requests              admin: requests (?status=pending)
  POST   /admin/elective-requests/{id}/approve admin: approve (the change is made) · …/reject
  POST   /admin/users/{id}/electives/reopen    admin: let the student choose freely again
"""
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_admin, get_current_user
from app.database import get_db
from app.models.electives import ElectiveChoice, ElectivePlan, ElectiveRequest
from app.models.task import Subject
from app.models.user import User
from app.services import content, observability

router = APIRouter(tags=["electives"])


def _student(user: User) -> None:
    if user.role != "student":
        raise HTTPException(status_code=403, detail="Only students choose electives")


async def _plan(db: AsyncSession, user_id) -> ElectivePlan:
    p = (await db.execute(select(ElectivePlan).where(ElectivePlan.user_id == user_id))).scalar_one_or_none()
    if p is None:
        p = ElectivePlan(user_id=user_id)
        db.add(p)
        await db.flush()
    return p


async def _elective(db: AsyncSession, subject_id) -> Subject:
    s = (await db.execute(select(Subject).where(Subject.id == subject_id))).scalar_one_or_none()
    if s is None:
        raise HTTPException(status_code=404, detail="Subject not found")
    if not s.elective:
        raise HTTPException(status_code=422, detail="Not an elective subject")
    return s


async def _choices(db: AsyncSession, user_id) -> dict:
    return {c.subject_id: c for c in (await db.execute(select(ElectiveChoice).where(ElectiveChoice.user_id == user_id))).scalars()}


def _name(s: Optional[Subject], lang) -> str:
    if s is None:
        return ""
    return (s.name_en or s.name) if lang == "en" else s.name


async def _request_out(db: AsyncSession, r: ElectiveRequest, lang, with_user: bool = False) -> dict:
    subs = {s.id: s for s in (await db.execute(select(Subject).where(
        Subject.id.in_([r.remove_subject_id, r.add_subject_id])))).scalars()}
    out = {"id": str(r.id), "status": r.status, "reason": r.reason or "", "admin_note": r.admin_note or "",
           "created_at": r.created_at.isoformat() + "Z", "decided_at": r.decided_at.isoformat() + "Z" if r.decided_at else None,
           "remove": {"subject_id": str(r.remove_subject_id), "name": _name(subs.get(r.remove_subject_id), lang),
                      "code": (subs.get(r.remove_subject_id).finki_code or subs.get(r.remove_subject_id).code) if subs.get(r.remove_subject_id) else "",
                      "semester": r.remove_semester},
           "add": {"subject_id": str(r.add_subject_id), "name": _name(subs.get(r.add_subject_id), lang),
                   "code": (subs.get(r.add_subject_id).finki_code or subs.get(r.add_subject_id).code) if subs.get(r.add_subject_id) else "",
                   "semester": r.add_semester},
           "move": r.add_subject_id == r.remove_subject_id}
    if with_user:
        u = (await db.execute(select(User).where(User.id == r.user_id))).scalar_one_or_none()
        out["student"] = {"user_id": str(r.user_id), "name": u.name if u else "", "email": u.email if u else ""}
        out["current"] = [{"subject_id": str(c.subject_id), "semester": c.semester}
                          for c in (await _choices(db, r.user_id)).values()]
    return out


async def _my_plan(db: AsyncSession, user: User, lang) -> dict:
    plan = (await db.execute(select(ElectivePlan).where(ElectivePlan.user_id == user.id))).scalar_one_or_none()
    choices = await _choices(db, user.id)
    reqs = (await db.execute(select(ElectiveRequest).where(ElectiveRequest.user_id == user.id)
                             .order_by(ElectiveRequest.created_at.desc()).limit(20))).scalars().all()
    return {"confirmed": bool(plan and plan.confirmed_at),
            "confirmed_at": plan.confirmed_at.isoformat() + "Z" if plan and plan.confirmed_at else None,
            "choices": [{"subject_id": str(c.subject_id), "semester": c.semester} for c in choices.values()],
            "pending": next(iter([await _request_out(db, r, lang) for r in reqs if r.status == "pending"]), None),
            "requests": [await _request_out(db, r, lang) for r in reqs]}


@router.get("/me/electives")
async def my_electives(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user),
                       lang: Optional[str] = Depends(content.reader_language)):
    return await _my_plan(db, user, lang)


class ChoiceIn(BaseModel):
    subject_id: uuid.UUID
    semester: int = Field(ge=1, le=8)


async def _free(db: AsyncSession, user: User) -> None:
    _student(user)
    plan = await _plan(db, user.id)
    if plan.confirmed_at:
        raise HTTPException(status_code=409, detail="Your electives are confirmed: send a request to the admin")


@router.post("/me/electives")
async def choose_elective(body: ChoiceIn, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user),
                          lang: Optional[str] = Depends(content.reader_language)):
    await _free(db, user)
    await _elective(db, body.subject_id)
    c = (await _choices(db, user.id)).get(body.subject_id)
    if c is None:
        db.add(ElectiveChoice(user_id=user.id, subject_id=body.subject_id, semester=body.semester))
    else:
        c.semester = body.semester
    await db.commit()
    await observability.activity("elective_choose", subject_id=body.subject_id, semester=body.semester)
    return await _my_plan(db, user, lang)


@router.delete("/me/electives/{subject_id}")
async def drop_elective(subject_id: uuid.UUID, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user),
                        lang: Optional[str] = Depends(content.reader_language)):
    await _free(db, user)
    c = (await _choices(db, user.id)).get(subject_id)
    if c is not None:
        await db.delete(c)
        await db.commit()
        await observability.activity("elective_drop", subject_id=subject_id)
    return await _my_plan(db, user, lang)


@router.post("/me/electives/confirm")
async def confirm_electives(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user),
                            lang: Optional[str] = Depends(content.reader_language)):
    await _free(db, user)
    if not await _choices(db, user.id):
        raise HTTPException(status_code=422, detail="Choose at least one elective first")
    (await _plan(db, user.id)).confirmed_at = datetime.utcnow()
    await db.commit()
    await observability.activity("electives_confirm")
    return await _my_plan(db, user, lang)


class RequestIn(BaseModel):
    remove_subject_id: uuid.UUID
    add_subject_id: uuid.UUID
    add_semester: int = Field(ge=1, le=8)
    reason: str = Field("", max_length=1000)


async def _check_change(db: AsyncSession, user_id, remove_id, add_id, add_semester) -> ElectiveChoice:
    choices = await _choices(db, user_id)
    old = choices.get(remove_id)
    if old is None:
        raise HTTPException(status_code=422, detail="That elective is not among yours")
    await _elective(db, add_id)
    if add_id == remove_id:
        if add_semester == old.semester:
            raise HTTPException(status_code=422, detail="Nothing would change")
    elif add_id in choices:
        raise HTTPException(status_code=422, detail="That elective is already among yours")
    return old


@router.post("/me/elective-requests", status_code=201)
async def request_change(body: RequestIn, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user),
                         lang: Optional[str] = Depends(content.reader_language)):
    """Both parts together: which elective goes out and which comes in (and in which semester)."""
    _student(user)
    plan = await _plan(db, user.id)
    if not plan.confirmed_at:
        raise HTTPException(status_code=409, detail="You are still choosing: change your electives directly")
    if (await db.execute(select(ElectiveRequest.id).where(ElectiveRequest.user_id == user.id,
                                                          ElectiveRequest.status == "pending"))).first():
        raise HTTPException(status_code=409, detail="You already have a request waiting for the admin")
    old = await _check_change(db, user.id, body.remove_subject_id, body.add_subject_id, body.add_semester)
    r = ElectiveRequest(user_id=user.id, remove_subject_id=old.subject_id, remove_semester=old.semester,
                        add_subject_id=body.add_subject_id, add_semester=body.add_semester, reason=body.reason.strip())
    db.add(r)
    await db.commit()
    await observability.activity("elective_request", request_id=r.id, remove=r.remove_subject_id, add=r.add_subject_id,
                                 semester=r.add_semester)
    return await _request_out(db, r, lang)


@router.delete("/me/elective-requests/{request_id}", status_code=204)
async def cancel_request(request_id: uuid.UUID, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    r = (await db.execute(select(ElectiveRequest).where(ElectiveRequest.id == request_id,
                                                        ElectiveRequest.user_id == user.id))).scalar_one_or_none()
    if r is None:
        raise HTTPException(status_code=404, detail="Request not found")
    if r.status != "pending":
        raise HTTPException(status_code=409, detail="The request was already decided")
    r.status, r.decided_at = "cancelled", datetime.utcnow()
    await db.commit()
    await observability.activity("elective_cancel", request_id=r.id)


# ------------------------------------------------------------------ admin

@router.get("/admin/elective-requests")
async def list_requests(status: Optional[str] = "pending", db: AsyncSession = Depends(get_db),
                        _: User = Depends(get_current_admin), lang: Optional[str] = Depends(content.reader_language)):
    q = select(ElectiveRequest).order_by(ElectiveRequest.created_at.desc()).limit(300)
    if status and status != "all":
        q = q.where(ElectiveRequest.status == status)
    rows = (await db.execute(q)).scalars().all()
    pending = (await db.execute(select(func.count()).where(ElectiveRequest.status == "pending"))).scalar_one()
    return {"requests": [await _request_out(db, r, lang, with_user=True) for r in rows], "pending": pending}


class DecisionIn(BaseModel):
    note: str = Field("", max_length=1000)


async def _pending(db: AsyncSession, request_id) -> ElectiveRequest:
    r = (await db.execute(select(ElectiveRequest).where(ElectiveRequest.id == request_id))).scalar_one_or_none()
    if r is None:
        raise HTTPException(status_code=404, detail="Request not found")
    if r.status != "pending":
        raise HTTPException(status_code=409, detail="The request was already decided")
    return r


@router.post("/admin/elective-requests/{request_id}/approve")
async def approve_request(request_id: uuid.UUID, body: DecisionIn, db: AsyncSession = Depends(get_db),
                          admin: User = Depends(get_current_admin), lang: Optional[str] = Depends(content.reader_language)):
    """The change is made: the elective goes out and the other one comes in (or moves to the new semester)."""
    r = await _pending(db, request_id)
    old = await _check_change(db, r.user_id, r.remove_subject_id, r.add_subject_id, r.add_semester)
    if r.add_subject_id == r.remove_subject_id:
        old.semester = r.add_semester
    else:
        await db.delete(old)
        await db.flush()
        db.add(ElectiveChoice(user_id=r.user_id, subject_id=r.add_subject_id, semester=r.add_semester))
    r.status, r.admin_note, r.decided_at, r.decided_by = "approved", body.note.strip(), datetime.utcnow(), admin.id
    await db.commit()
    await observability.activity("elective_approve", request_id=r.id, student=r.user_id)
    return await _request_out(db, r, lang, with_user=True)


@router.post("/admin/elective-requests/{request_id}/reject")
async def reject_request(request_id: uuid.UUID, body: DecisionIn, db: AsyncSession = Depends(get_db),
                         admin: User = Depends(get_current_admin), lang: Optional[str] = Depends(content.reader_language)):
    r = await _pending(db, request_id)
    r.status, r.admin_note, r.decided_at, r.decided_by = "rejected", body.note.strip(), datetime.utcnow(), admin.id
    await db.commit()
    await observability.activity("elective_reject", request_id=r.id, student=r.user_id)
    return await _request_out(db, r, lang, with_user=True)


@router.post("/admin/users/{user_id}/electives/reopen")
async def reopen_choice(user_id: uuid.UUID, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_admin)):
    """Let the student choose freely again (e.g. a new study year); their electives stay until they change them."""
    plan = (await db.execute(select(ElectivePlan).where(ElectivePlan.user_id == user_id))).scalar_one_or_none()
    if plan is not None:
        plan.confirmed_at = None
        await db.commit()
        await observability.activity("electives_reopen", student=user_id)
    return {"ok": True}
