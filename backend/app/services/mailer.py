"""
Sending e-mail. Three modes (settings.MAIL_MODE):
  preview    nothing leaves the server; deliveries are stored as "preview" and can be read in the app (testing)
  smtp       the faculty's SMTP server (STARTTLS / SSL / plain)
  microsoft  Microsoft 365 via Graph sendMail, with the app registration used for sign-in (Mail.Send permission)

`dispatch(email_id)` sends an approved e-mail's queued deliveries in the background, each in the recipient's language.
"""
import asyncio
import base64
import logging
import smtplib
import ssl
import time
from dataclasses import dataclass
from datetime import datetime
from email.message import EmailMessage
from email.utils import formataddr, make_msgid

import httpx
from sqlalchemy import func, select, update

from app.config import settings
from app.database import AsyncSessionLocal
from app.models.comms import Email, EmailDelivery

log = logging.getLogger("ale")


@dataclass
class Outgoing:
    to: str
    subject: str
    text: str
    attachment: tuple[str, str, bytes] | None = None  # (name, content type, data)


def mode() -> str:
    m = (settings.MAIL_MODE or "preview").lower()
    return m if m in ("preview", "smtp", "microsoft") else "preview"


def configured() -> tuple[bool, str]:
    """(ready, what is missing) for the admin page."""
    m = mode()
    if m == "smtp" and not settings.SMTP_HOST:
        return False, "SMTP_HOST"
    if m == "microsoft" and not (settings.MS_CLIENT_ID and settings.MS_CLIENT_SECRET and settings.MS_TENANT_ID
                                 and settings.MS_TENANT_ID != "organizations"):
        return False, "MS_CLIENT_ID / MS_CLIENT_SECRET / MS_TENANT_ID (the faculty's tenant id)"
    return True, ""


# ---------------------------------------------------------------------------
# Transports
# ---------------------------------------------------------------------------

def _smtp_send(msgs: list[Outgoing]) -> list[str | None]:
    """One connection for a batch. Returns an error per message (None = sent)."""
    sec = (settings.SMTP_SECURITY or "starttls").lower()
    ctx = ssl.create_default_context()
    errors: list[str | None] = []
    cls = smtplib.SMTP_SSL if sec == "ssl" else smtplib.SMTP
    kw = {"context": ctx} if sec == "ssl" else {}
    with cls(settings.SMTP_HOST, settings.SMTP_PORT, timeout=30, **kw) as s:
        if sec == "starttls":
            s.starttls(context=ctx)
        if settings.SMTP_USER:
            s.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        for m in msgs:
            em = EmailMessage()
            em["From"] = formataddr((settings.MAIL_FROM_NAME, settings.MAIL_FROM))
            em["To"] = m.to
            em["Subject"] = m.subject
            em["Message-ID"] = make_msgid(domain=settings.MAIL_FROM.split("@")[-1] or "localhost")
            em.set_content(m.text)
            if m.attachment:
                name, ctype, data = m.attachment
                main, _, sub = ctype.partition("/")
                em.add_attachment(data, maintype=main, subtype=sub or "octet-stream", filename=name)
            try:
                s.send_message(em)
                errors.append(None)
            except smtplib.SMTPException as e:
                errors.append(str(e)[:500])
    return errors


_token: tuple[str, float] | None = None


async def _graph_token(client: httpx.AsyncClient) -> str:
    global _token
    if _token and _token[1] > time.time() + 60:
        return _token[0]
    authority = settings.MS_AUTHORITY.rstrip("/").removesuffix("/v2.0") if settings.MS_AUTHORITY else \
        f"https://login.microsoftonline.com/{settings.MS_TENANT_ID}"
    r = await client.post(f"{authority}/oauth2/v2.0/token", data={
        "grant_type": "client_credentials", "client_id": settings.MS_CLIENT_ID, "client_secret": settings.MS_CLIENT_SECRET,
        "scope": "https://graph.microsoft.com/.default"})
    r.raise_for_status()
    data = r.json()
    _token = (data["access_token"], time.time() + int(data.get("expires_in", 3600)))
    return _token[0]


async def _graph_send(msgs: list[Outgoing]) -> list[str | None]:
    errors: list[str | None] = []
    async with httpx.AsyncClient(timeout=30) as client:
        token = await _graph_token(client)
        for m in msgs:
            message = {"subject": m.subject, "body": {"contentType": "Text", "content": m.text},
                       "toRecipients": [{"emailAddress": {"address": m.to}}]}
            if m.attachment:
                name, ctype, data = m.attachment
                message["attachments"] = [{"@odata.type": "#microsoft.graph.fileAttachment", "name": name,
                                           "contentType": ctype, "contentBytes": base64.b64encode(data).decode()}]
            r = await client.post(f"https://graph.microsoft.com/v1.0/users/{settings.MAIL_FROM}/sendMail",
                                  headers={"Authorization": f"Bearer {token}"},
                                  json={"message": message, "saveToSentItems": False})
            errors.append(None if r.status_code in (200, 202) else f"Graph {r.status_code}: {r.text[:300]}")
    return errors


async def send(msgs: list[Outgoing]) -> list[str | None]:
    """Send a batch; returns an error (or None) per message. In preview mode nothing is sent."""
    m = mode()
    if m == "preview" or not msgs:
        return [None] * len(msgs)
    ok, missing = configured()
    if not ok:
        return [f"E-mail is not configured: {missing}"] * len(msgs)
    try:
        if m == "smtp":
            return await asyncio.to_thread(_smtp_send, msgs)
        return await _graph_send(msgs)
    except Exception as e:  # the whole batch failed (server unreachable, wrong password, ...)
        log.warning("mail batch failed: %s", e)
        return [f"{type(e).__name__}: {e}"[:500]] * len(msgs)


# ---------------------------------------------------------------------------
# Sending an approved e-mail
# ---------------------------------------------------------------------------

BATCH = 25


def compose(email: Email, lang: str) -> tuple[str, str]:
    """Subject and text in the recipient's language (Macedonian when the English version is empty)."""
    if lang == "en" and (email.subject_en.strip() or email.body_en.strip()):
        return email.subject_en.strip() or email.subject_mk, email.body_en.strip() or email.body_mk
    return email.subject_mk.strip() or email.subject_en, email.body_mk.strip() or email.body_en


async def dispatch(email_id) -> None:
    try:
        async with AsyncSessionLocal() as db:
            email = (await db.execute(select(Email).where(Email.id == email_id))).scalar_one()
            queued = (await db.execute(select(EmailDelivery).where(
                EmailDelivery.email_id == email_id, EmailDelivery.status == "queued"))).scalars().all()
            attach = (email.attachment_name, email.attachment_type, email.attachment) if email.attachment else None
            batch_rows = [(d.id, d.address, *compose(email, d.lang)) for d in queued]
        preview = mode() == "preview"
        for i in range(0, len(batch_rows), BATCH):
            chunk = batch_rows[i:i + BATCH]
            errors = await send([Outgoing(addr, subj, text, attach) for _, addr, subj, text in chunk])
            now = datetime.utcnow()
            async with AsyncSessionLocal() as db:
                for (did, *_), err in zip(chunk, errors):
                    await db.execute(update(EmailDelivery).where(EmailDelivery.id == did).values(
                        status="failed" if err else ("preview" if preview else "sent"), error=err or "", sent_at=now))
                await db.commit()
        async with AsyncSessionLocal() as db:
            failed = (await db.execute(select(func.count()).select_from(EmailDelivery).where(
                EmailDelivery.email_id == email_id, EmailDelivery.status == "failed"))).scalar_one()
            await db.execute(update(Email).where(Email.id == email_id).values(
                status="sent", sent_at=datetime.utcnow(), failed=failed))
            await db.commit()
    except Exception:
        log.exception("sending e-mail %s failed", email_id)


def dispatch_later(email_id) -> None:
    asyncio.get_running_loop().create_task(dispatch(email_id))
