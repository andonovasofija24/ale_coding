"""
Course e-mail with approval.

  GET  /courses/{id}/emails              staff: drafts and sent messages
  POST /courses/{id}/emails              staff: a new message (written by hand)
  GET  /emails/{id}                      staff: one message with its recipients
  PUT  /emails/{id}                      staff: edit a draft (both languages, audience, group)
  POST /emails/{id}/ai                   staff: let AI improve the draft (both languages) — still only a draft
  POST /emails/{id}/send                 staff: approve and send
  POST /emails/{id}/cancel               staff: don't send
  GET  /courses/{id}/announcements       everyone in the course: what was sent to them (in their language)
  GET  /admin/mail                       admin: mode, configuration, last deliveries (the "preview inbox")
  POST /admin/mail/test                  admin: send a test message
  POST /admin/reminders/run              admin: look for due reminders now
"""
import uuid
from datetime import timezone
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import access
from app.core.deps import get_current_admin, get_current_user
from app.database import get_db
from app.models.comms import Email, EmailDelivery
from app.models.course import Assignment, Course, CourseGroup
from app.models.user import User
from app.services import agent_service, emails, gradesheet, mailer, reminders

router = APIRouter(tags=["emails"])


def _iso(dt):
    return dt.replace(tzinfo=timezone.utc).isoformat() if dt else None


class EmailIn(BaseModel):
    subject_mk: str = Field("", max_length=300)
    body_mk: str = Field("", max_length=20_000)
    subject_en: str = Field("", max_length=300)
    body_en: str = Field("", max_length=20_000)
    audience: Literal["students", "staff"] = "students"
    group_id: Optional[uuid.UUID] = None


class AIIn(BaseModel):
    notes: str = Field("", max_length=1000)


class TestIn(BaseModel):
    to: EmailStr


def _out(e: Email, assignment_title: str | None = None, full: bool = False) -> dict:
    out = {"id": str(e.id), "course_id": str(e.course_id), "kind": e.kind, "audience": e.audience,
           "group_id": str(e.group_id) if e.group_id else None,
           "assignment_id": str(e.assignment_id) if e.assignment_id else None, "assignment_title": assignment_title,
           "subject_mk": e.subject_mk, "subject_en": e.subject_en, "status": e.status,
           "created_at": _iso(e.created_at), "sent_at": _iso(e.sent_at), "recipients": e.recipients, "failed": e.failed,
           "automatic": e.created_by is None, "attachment_name": e.attachment_name or None}
    if full:
        out.update({"body_mk": e.body_mk, "body_en": e.body_en})
    return out


async def _staff_email(db: AsyncSession, user: User, email_id) -> tuple[Email, Course]:
    e = (await db.execute(select(Email).where(Email.id == email_id))).scalar_one_or_none()
    if e is None:
        raise HTTPException(status_code=404, detail="Message not found")
    course, _ = await access.load_course(db, user, e.course_id, access.COURSE_STAFF)
    return e, course


@router.get("/courses/{course_id}/emails")
async def list_emails(course_id: uuid.UUID, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    await access.load_course(db, user, course_id, access.COURSE_STAFF)
    rows = (await db.execute(select(Email, Assignment.title).outerjoin(Assignment, Assignment.id == Email.assignment_id)
                             .where(Email.course_id == course_id, Email.kind != "reminder")
                             .order_by((Email.status == "draft").desc(), Email.created_at.desc()).limit(200))).all()
    reminders_sent = (await db.execute(select(func.coalesce(func.sum(Email.recipients), 0)).where(
        Email.course_id == course_id, Email.kind == "reminder"))).scalar_one()
    ok, missing = mailer.configured()
    return {"mode": mailer.mode(), "configured": ok, "reminders_sent": int(reminders_sent),
            "emails": [_out(e, t) for e, t in rows]}


@router.post("/courses/{course_id}/emails", status_code=201)
async def new_email(course_id: uuid.UUID, body: EmailIn, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    course, _ = await access.load_course(db, user, course_id, access.COURSE_STAFF)
    e = await emails.draft(db, course, "custom", None, user, audience=body.audience)
    await _apply(db, e, body)
    await db.commit()
    return _out(e, full=True)


async def _apply(db: AsyncSession, e: Email, body: EmailIn) -> None:
    if body.group_id and not (await db.execute(select(CourseGroup.id).where(
            CourseGroup.id == body.group_id, CourseGroup.course_id == e.course_id))).first():
        raise HTTPException(status_code=422, detail="Group not found")
    e.subject_mk, e.body_mk, e.subject_en, e.body_en = body.subject_mk, body.body_mk, body.subject_en, body.body_en
    e.audience, e.group_id = body.audience, body.group_id if body.audience == "students" else None


@router.get("/emails/{email_id}")
async def get_email(email_id: uuid.UUID, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    e, course = await _staff_email(db, user, email_id)
    title = (await db.execute(select(Assignment.title).where(Assignment.id == e.assignment_id))).scalar_one_or_none() if e.assignment_id else None
    out = _out(e, title, full=True)
    if e.status == "draft":
        rec = await emails.recipients(db, course, e.audience, e.group_id)
        out["would_reach"] = {"total": len(rec), "mk": sum(1 for r in rec if r[2] != "en"), "en": sum(1 for r in rec if r[2] == "en")}
    else:
        rows = (await db.execute(select(EmailDelivery).where(EmailDelivery.email_id == e.id).order_by(EmailDelivery.address))).scalars().all()
        out["deliveries"] = [{"address": d.address, "lang": d.lang, "status": d.status, "error": d.error} for d in rows]
    return out


@router.put("/emails/{email_id}")
async def update_email(email_id: uuid.UUID, body: EmailIn, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    e, _ = await _staff_email(db, user, email_id)
    if e.status != "draft":
        raise HTTPException(status_code=409, detail="Only drafts can be changed")
    await _apply(db, e, body)
    await db.commit()
    return await get_email(email_id, db, user)


@router.post("/emails/{email_id}/ai")
async def improve_email(email_id: uuid.UUID, body: AIIn, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    e, course = await _staff_email(db, user, email_id)
    if e.status != "draft":
        raise HTTPException(status_code=409, detail="Only drafts can be changed")
    facts = [f"Course: {course.code} — {course.name}", f"Teacher: {user.name}", f"Kind of message: {e.kind}"]
    if e.assignment_id:
        a = (await db.execute(select(Assignment).where(Assignment.id == e.assignment_id))).scalar_one_or_none()
        if a is not None:
            facts += [f"Assignment: {a.title}", f"Deadline (mk): {emails.when(a.due_at, 'mk')}",
                      f"Deadline (en): {emails.when(a.due_at, 'en')}", f"Link: {emails.link(f'/assignments/{a.id}')}"]
    current = {k: getattr(e, k) for k in ("subject_mk", "body_mk", "subject_en", "body_en")}
    try:
        new = await agent_service.draft_email("\n".join(facts), current, body.notes)
    except agent_service.AIUnavailable:
        raise
    except Exception as ex:
        raise HTTPException(status_code=502, detail="Could not improve the message") from ex
    for k, v in new.items():
        if v:
            setattr(e, k, v[:300] if k.startswith("subject") else v)
    await db.commit()
    return await get_email(email_id, db, user)


@router.post("/emails/{email_id}/send")
async def send_email(email_id: uuid.UUID, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    """Approve and send: each recipient gets the version in their group's language."""
    e, course = await _staff_email(db, user, email_id)
    if e.status != "draft":
        raise HTTPException(status_code=409, detail="This message was already sent or cancelled")
    if not (e.subject_mk.strip() or e.subject_en.strip()) or not (e.body_mk.strip() or e.body_en.strip()):
        raise HTTPException(status_code=422, detail="Write a subject and a message first")
    if e.kind == "gradesheet":  # the attached sheet is made now, with the latest points
        a = (await db.execute(select(Assignment).where(Assignment.id == e.assignment_id))).scalar_one_or_none() if e.assignment_id else None
        e.attachment = await gradesheet.build(db, course)
        e.attachment_name = gradesheet.file_name(course, a)
        e.attachment_type = gradesheet.XLSX
    n = await emails.queue(db, e, course)
    if n == 0:
        raise HTTPException(status_code=422, detail="Nobody to send it to")
    e.approved_by = user.id
    await db.commit()
    mailer.dispatch_later(e.id)
    return _out(e)


@router.post("/emails/{email_id}/cancel")
async def cancel_email(email_id: uuid.UUID, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    e, _ = await _staff_email(db, user, email_id)
    if e.status != "draft":
        raise HTTPException(status_code=409, detail="This message was already sent or cancelled")
    e.status = "cancelled"
    await db.commit()
    return _out(e)


@router.get("/courses/{course_id}/announcements")
async def announcements(course_id: uuid.UUID, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    """Messages sent to the students of the course — for a student only those addressed to them, in their language."""
    course, role = await access.load_course(db, user, course_id)
    q = select(Email).where(Email.course_id == course.id, Email.status == "sent", Email.audience == "students",
                            Email.kind != "reminder")
    lang = course.language or "mk"
    if role == "student":
        m = await access.membership(db, user, course.id)
        q = q.where((Email.group_id.is_(None)) | (Email.group_id == m.group_id))
        if m.group_id:
            glang = (await db.execute(select(CourseGroup.language).where(CourseGroup.id == m.group_id))).scalar_one_or_none()
            lang = glang or lang
    rows = (await db.execute(q.order_by(Email.sent_at.desc()).limit(100))).scalars().all()
    out = []
    for e in rows:
        subject, body = mailer.compose(e, lang)
        out.append({"id": str(e.id), "subject": subject, "body": body, "sent_at": _iso(e.sent_at), "kind": e.kind,
                    "assignment_id": str(e.assignment_id) if e.assignment_id else None})
    return out


# ---------------------------------------------------------------------------
# Admin
# ---------------------------------------------------------------------------

@router.get("/admin/mail")
async def mail_status(db: AsyncSession = Depends(get_db), _: User = Depends(get_current_admin)):
    ok, missing = mailer.configured()
    rows = (await db.execute(select(EmailDelivery, Email, Course.code).join(Email, Email.id == EmailDelivery.email_id)
                             .join(Course, Course.id == Email.course_id)
                             .order_by(EmailDelivery.sent_at.desc().nullsfirst()).limit(100))).all()
    return {"mode": mailer.mode(), "configured": ok, "missing": missing,
            "from": mailer.settings.MAIL_FROM,
            "deliveries": [{"address": d.address, "lang": d.lang, "status": d.status, "error": d.error,
                            "sent_at": _iso(d.sent_at), "course": code, "kind": e.kind,
                            "subject": mailer.compose(e, d.lang)[0], "body": mailer.compose(e, d.lang)[1]} for d, e, code in rows]}


@router.post("/admin/mail/test")
async def mail_test(body: TestIn, _: User = Depends(get_current_admin)):
    err = (await mailer.send([mailer.Outgoing(str(body.to), "ALE — test", "Ова е пробна порака од ALE.\nThis is a test message from ALE.")]))[0]
    if err:
        raise HTTPException(status_code=502, detail=err)
    return {"mode": mailer.mode(), "sent": mailer.mode() != "preview"}


@router.post("/admin/reminders/run")
async def run_reminders(_: User = Depends(get_current_admin)):
    return {"sent": await reminders.run_once()}
