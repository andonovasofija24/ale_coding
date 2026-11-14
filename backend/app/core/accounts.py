"""
The type of an account from its e-mail (no choosing, no asking):

  …@students.finki.ukim.mk   → student  (and, on their own, the spaces of their study plan)
  …@finki.ukim.mk            → teacher  (with no permissions anywhere until the admin adds them to a subject)
  anything else              → may not sign up (the admin can still make such an account by hand)

The domains come from STUDENT_EMAIL_DOMAINS / TEACHER_EMAIL_DOMAINS (comma-separated, exact domains). Admin accounts
are never changed by this.
"""
from typing import Optional

from app.config import settings


def _domains(v: str) -> set[str]:
    return {d.strip().lower().lstrip("@") for d in (v or "").split(",") if d.strip()}


def account_for_email(email: str) -> Optional[str]:
    """"student" / "teacher" / None (a domain we don't take)."""
    domain = (email or "").strip().lower().rpartition("@")[2]
    if not domain:
        return None
    if domain in _domains(settings.STUDENT_EMAIL_DOMAINS):
        return "student"
    if domain in _domains(settings.TEACHER_EMAIL_DOMAINS):
        return "teacher"
    return None
