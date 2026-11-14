"""
A student's electives. The student never changes them directly: every change is a request that the admin approves
or rejects — add an elective (in a semester), take one out, or move one to another semester (or one out and another
in, together). Until the admin approves, nothing changes (also not who is in the subject's space).

  GET    /me/electives                         my plan: my electives (approved), my requests (pending first)
  POST   /me/electives                         a request: add this elective / move it to this semester
  DELETE /me/electives/{subject_id}            a request: take it out (or cancel my pending request to add it)
  POST   /me/elective-requests                 a request with both parts: {remove_subject_id?, add_subject_id?, …}
  DELETE /me/elective-requests/{id}            cancel my pending request
  GET    /admin/elective-requests              admin: requests (?status=pending)
  POST   /admin/elective-requests/{id}/approve admin: approve (the change is made) · …/reject
  (POST /me/electives/confirm and /admin/users/{id}/electives/reopen remain for older clients; they change nothing)
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
from app.services import content, observability, spaces

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


def _part(subs: dict, sid, semester, lang) -> Optional[dict]:
    if sid is None:
        return None
    sub = subs.get(sid)
    return {"subject_id": str(sid), "name": _name(sub, lang), "code": (sub.finki_code or sub.code) if sub else "",
            "semester": semester}


def _kind(r: ElectiveRequest) -> str:
    if r.add_subject_id and r.remove_subject_id:
        return "move" if r.add_subject_id == r.remove_subject_id else "swap"
    return "add" if r.add_subject_id else "remove"


async def _request_out(db: AsyncSession, r: ElectiveRequest, lang, with_user: bool = False) -> dict:
    ids = [x for x in (r.remove_subject_id, r.add_subject_id) if x]
    subs = {s.id: s for s in (await db.execute(select(Subject).where(Subject.id.in_(ids)))).scalars()} if ids else {}
    out = {"id": str(r.id), "status": r.status, "reason": r.reason or "", "admin_note": r.admin_note or "",
           "created_at": r.created_at.isoformat() + "Z", "decided_at": r.decided_at.isoformat() + "Z" if r.decided_at else None,
           "kind": _kind(r), "remove": _part(subs, r.remove_subject_id, r.remove_semester, lang),
           "add": _part(subs, r.add_subject_id, r.add_semester, lang), "move": _kind(r) == "move"}
    if with_user:
        u = (await db.execute(select(User).where(User.id == r.user_id))).scalar_one_or_none()
        out["student"] = {"user_id": str(r.user_id), "name": u.name if u else "", "email": u.email if u else ""}
        out["current"] = [{"subject_id": str(c.subject_id), "semester": c.semester}
                          for c in (await _choices(db, r.user_id)).values()]
    return out


async def _pending_of(db: AsyncSession, user_id) -> list[ElectiveRequest]:
    return list((await db.execute(select(ElectiveRequest).where(ElectiveRequest.user_id == user_id,
                                                                ElectiveRequest.status == "pending")
                                  .order_by(ElectiveRequest.created_at))).scalars())


async def _my_plan(db: AsyncSession, user: User, lang) -> dict:
    choices = await _choices(db, user.id)
    reqs = (await db.execute(select(ElectiveRequest).where(ElectiveRequest.user_id == user.id)
                             .order_by(ElectiveRequest.created_at.desc()).limit(30))).scalars().all()
    pend = [await _request_out(db, r, lang) for r in reqs if r.status == "pending"]
    return {"choices": [{"subject_id": str(c.subject_id), "semester": c.semester} for c in choices.values()],
            "pending_requests": pend,
            "pending": pend[0] if pend else None,
            "requests": [await _request_out(db, r, lang) for r in reqs],
            # (older clients) there is no "confirm" any more: every change is a request
            "confirmed": True, "confirmed_at": None}


@router.get("/me/electives")
async def my_electives(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user),
                       lang: Optional[str] = Depends(content.reader_language)):
    _student(user)
    return await _my_plan(db, user, lang)


async def _check_change(db: AsyncSession, user_id, remove_id, add_id, add_semester, *, deciding=False):
    """Is this change possible now? Returns the elective that goes out (or None). Also when the admin decides:
    the plan may have changed since the request was sent."""
    if not remove_id and not add_id:
        raise HTTPException(status_code=422, detail="Nothing would change")
    choices = await _choices(db, user_id)
    old = None
    if remove_id:
        old = choices.get(remove_id)
        if old is None:
            raise HTTPException(status_code=422, detail="That elective is not among yours")
    if add_id:
        await _elective(db, add_id)
        if add_semester is None:
            raise HTTPException(status_code=422, detail="Choose the semester")
        if add_id == remove_id:
            if add_semester == old.semester:
                raise HTTPException(status_code=422, detail="Nothing would change")
        elif add_id in choices:
            raise HTTPException(status_code=422, detail="That elective is already among yours")
    if not deciding:
        busy = {x for r in await _pending_of(db, user_id) for x in (r.remove_subject_id, r.add_subject_id) if x}
        if (remove_id and remove_id in busy) or (add_id and add_id in busy):
            raise HTTPException(status_code=409, detail="You already have a request for this elective")
    return old


async def _send(db: AsyncSession, user: User, remove_id, add_id, add_semester, reason: str) -> ElectiveRequest:
    _student(user)
    old = await _check_change(db, user.id, remove_id, add_id, add_semester)
    r = ElectiveRequest(user_id=user.id, remove_subject_id=old.subject_id if old else None,
                        remove_semester=old.semester if old else None, add_subject_id=add_id,
                        add_semester=add_semester if add_id else None, reason=(reason or "").strip())
    db.add(r)
    await db.commit()
    await observability.activity("elective_request", request_id=r.id, kind=_kind(r), remove=r.remove_subject_id,
                                 add=r.add_subject_id, semester=r.add_semester)
    return r


class ChoiceIn(BaseModel):
    subject_id: uuid.UUID
    semester: int = Field(ge=1, le=8)
    reason: str = Field("", max_length=1000)


@router.post("/me/electives")
async def choose_elective(body: ChoiceIn, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user),
                          lang: Optional[str] = Depends(content.reader_language)):
    """A request to the admin: add this elective in this semester (or, if it is already mine, move it there)."""
    _student(user)
    mine = (await _choices(db, user.id)).get(body.subject_id)
    await _send(db, user, body.subject_id if mine else None, body.subject_id, body.semester, body.reason)
    return await _my_plan(db, user, lang)


@router.delete("/me/electives/{subject_id}")
async def drop_elective(subject_id: uuid.UUID, reason: str = "", db: AsyncSession = Depends(get_db),
                        user: User = Depends(get_current_user), lang: Optional[str] = Depends(content.reader_language)):
    """A request to the admin to take it out — or, if it isn't mine yet, cancel my waiting request to add it."""
    _student(user)
    if (await _choices(db, user.id)).get(subject_id) is None:
        for r in await _pending_of(db, user.id):
            if r.add_subject_id == subject_id and not r.remove_subject_id:
                r.status, r.decided_at = "cancelled", datetime.utcnow()
                await db.commit()
                await observability.activity("elective_cancel", request_id=r.id)
                return await _my_plan(db, user, lang)
        raise HTTPException(status_code=422, detail="That elective is not among yours")
    await _send(db, user, subject_id, None, None, reason[:1000])
    return await _my_plan(db, user, lang)


@router.post("/me/electives/confirm")
async def confirm_electives(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user),
                            lang: Optional[str] = Depends(content.reader_language)):
    """(Older clients.) Nothing to confirm any more: every change is already a request."""
    _student(user)
    return await _my_plan(db, user, lang)


class RequestIn(BaseModel):
    remove_subject_id: Optional[uuid.UUID] = None
    add_subject_id: Optional[uuid.UUID] = None
    add_semester: Optional[int] = Field(None, ge=1, le=8)
    reason: str = Field("", max_length=1000)


@router.post("/me/elective-requests", status_code=201)
async def request_change(body: RequestIn, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user),
                         lang: Optional[str] = Depends(content.reader_language)):
    """One elective out and/or one in (the same one in both = another semester)."""
    r = await _send(db, user, body.remove_subject_id, body.add_subject_id, body.add_semester, body.reason)
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
    """The change is made: the elective comes in / goes out / moves to the new semester; the student's subject
    spaces follow."""
    r = await _pending(db, request_id)
    old = await _check_change(db, r.user_id, r.remove_subject_id, r.add_subject_id, r.add_semester, deciding=True)
    if r.add_subject_id and r.add_subject_id == r.remove_subject_id:
        old.semester = r.add_semester
    else:
        if old is not None:
            await db.delete(old)
            await db.flush()
        if r.add_subject_id:
            db.add(ElectiveChoice(user_id=r.user_id, subject_id=r.add_subject_id, semester=r.add_semester))
    r.status, r.admin_note, r.decided_at, r.decided_by = "approved", body.note.strip(), datetime.utcnow(), admin.id
    await db.flush()
    await spaces.sync_students(db, r.user_id)
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
