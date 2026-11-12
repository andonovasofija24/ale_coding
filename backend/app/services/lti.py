"""
LTI 1.3 / LTI Advantage plumbing: ALE's signing key, checking the platform's id_token, service tokens, and the two
services ALE uses — Assignment and Grade Services (points back to Moodle's gradebook) and Names and Role
Provisioning (the course's participant list). The HTTP endpoints are in routers/lti.py.

Standards: IMS LTI 1.3 Core, LTI Advantage (Deep Linking 2.0, AGS 2.0, NRPS 2.0), LTI Dynamic Registration 1.0.
"""
import base64
import re
import secrets
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

import httpx
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from jose import jwt
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core import permissions as P
from app.models.course import CourseMember
from app.models.lti import LtiContext, LtiNonce, LtiPlatform, LtiToolKey, LtiUser
from app.models.user import User
from app.services import observability
from app.services.ai_config import decrypt_key, encrypt_key

CLAIM = "https://purl.imsglobal.org/spec/lti/claim/"
AGS_CLAIM = "https://purl.imsglobal.org/spec/lti-ags/claim/endpoint"
NRPS_CLAIM = "https://purl.imsglobal.org/spec/lti-nrps/claim/namesroleservice"
DL_CLAIM = "https://purl.imsglobal.org/spec/lti-dl/claim/"
TOOL_CONFIG = "https://purl.imsglobal.org/spec/lti-tool-configuration"

SCOPE_LINEITEM = "https://purl.imsglobal.org/spec/lti-ags/scope/lineitem"
SCOPE_RESULT = "https://purl.imsglobal.org/spec/lti-ags/scope/result.readonly"
SCOPE_SCORE = "https://purl.imsglobal.org/spec/lti-ags/scope/score"
SCOPE_NRPS = "https://purl.imsglobal.org/spec/lti-nrps/scope/contextmembership.readonly"
ALL_SCOPES = [SCOPE_LINEITEM, SCOPE_RESULT, SCOPE_SCORE, SCOPE_NRPS]

ROLE_MEMBERSHIP = "http://purl.imsglobal.org/vocab/lis/v2/membership#"
ROLE_TA = "http://purl.imsglobal.org/vocab/lis/v2/membership/Instructor#TeachingAssistant"
ROLE_GRADER = "http://purl.imsglobal.org/vocab/lis/v2/membership/Instructor#Grader"
ROLE_INST_ADMIN = "http://purl.imsglobal.org/vocab/lis/v2/institution/person#Administrator"
ROLE_SYS_ADMIN = "http://purl.imsglobal.org/vocab/lis/v2/system/person#Administrator"



class LtiError(Exception):
    """A launch or service call that can't go on; `code` is shown to the person (translated in the app)."""
    def __init__(self, code: str, detail: str = ""):
        super().__init__(detail or code)
        self.code, self.detail = code, detail


# ---------------------------------------------------------------- URLs ALE gives to Moodle

def base() -> str:
    return settings.PUBLIC_URL.rstrip("/")


def tool_urls() -> dict:
    b = base()
    return {"login": b + "/lti/login", "launch": b + "/lti/launch", "jwks": b + "/lti/jwks",
            "deep_link": b + "/lti/launch", "domain": re.sub(r"^https?://", "", b).split("/")[0]}


# ---------------------------------------------------------------- ALE's own key

def _b64(n: int) -> str:
    raw = n.to_bytes((n.bit_length() + 7) // 8, "big")
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


async def tool_key(db: AsyncSession) -> LtiToolKey:
    """The active signing key; made on first use (RSA 2048). Kept encrypted with SECRET_KEY."""
    k = (await db.execute(select(LtiToolKey).where(LtiToolKey.active.is_(True))
                          .order_by(LtiToolKey.created_at.desc()))).scalars().first()
    if k and decrypt_key(k.private_pem_encrypted):
        return k
    if k:  # SECRET_KEY changed: the old key can't be used any more
        k.active = False
    priv = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = priv.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                             serialization.NoEncryption()).decode()
    nums = priv.public_key().public_numbers()
    kid = secrets.token_hex(8)
    k = LtiToolKey(kid=kid, private_pem_encrypted=encrypt_key(pem),
                   public_jwk={"kty": "RSA", "alg": "RS256", "use": "sig", "kid": kid, "e": _b64(nums.e), "n": _b64(nums.n)})
    db.add(k)
    await db.commit()
    return k


async def jwks(db: AsyncSession) -> dict:
    await tool_key(db)
    keys = (await db.execute(select(LtiToolKey).where(LtiToolKey.active.is_(True)))).scalars().all()
    return {"keys": [k.public_jwk for k in keys]}


async def sign(db: AsyncSession, claims: dict) -> str:
    k = await tool_key(db)
    return jwt.encode(claims, decrypt_key(k.private_pem_encrypted), algorithm="RS256", headers={"kid": k.kid})


# ---------------------------------------------------------------- the platform's id_token

_jwks_cache: dict[str, tuple[dict, float]] = {}


async def _platform_keys(url: str, force: bool = False) -> dict:
    if force or url not in _jwks_cache or _jwks_cache[url][1] < time.time():
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.get(url)
            r.raise_for_status()
            _jwks_cache[url] = (r.json(), time.time() + 3600)
    return _jwks_cache[url][0]


async def find_platform(db: AsyncSession, issuer: str, client_id: Optional[str]) -> LtiPlatform:
    q = select(LtiPlatform).where(LtiPlatform.issuer.in_([issuer, issuer.rstrip("/")]), LtiPlatform.active.is_(True))
    if client_id:
        q = q.where(LtiPlatform.client_id == client_id)
    rows = (await db.execute(q)).scalars().all()
    if len(rows) != 1:
        raise LtiError("unknown_platform", f"{issuer} / {client_id}")
    return rows[0]


async def verify_id_token(db: AsyncSession, token: str) -> tuple[LtiPlatform, dict]:
    try:
        unverified = jwt.get_unverified_claims(token)
        header = jwt.get_unverified_header(token)
    except Exception:
        raise LtiError("bad_token")
    aud = unverified.get("aud")
    client_id = unverified.get("azp") or (aud if isinstance(aud, str) else (aud[0] if aud and len(aud) == 1 else None))
    platform = await find_platform(db, unverified.get("iss", ""), client_id)
    try:
        keys = await _platform_keys(platform.jwks_url)
        if not any(k.get("kid") == header.get("kid") for k in keys.get("keys", [])):
            keys = await _platform_keys(platform.jwks_url, force=True)  # the platform rotated its keys
        claims = jwt.decode(token, keys, algorithms=["RS256"], audience=platform.client_id, issuer=platform.issuer,
                            options={"verify_at_hash": False, "leeway": 60})
    except LtiError:
        raise
    except Exception as e:
        observability.log_event("lti_token_invalid", error=f"{type(e).__name__}: {e}"[:300])
        raise LtiError("bad_token")
    if isinstance(claims.get("aud"), list) and len(claims["aud"]) > 1 and claims.get("azp") != platform.client_id:
        raise LtiError("bad_token", "azp")
    dep = claims.get(CLAIM + "deployment_id", "")
    if not dep or (platform.deployment_ids and dep not in platform.deployment_ids):
        raise LtiError("unknown_deployment", dep)
    if claims.get(CLAIM + "version") != "1.3.0":
        raise LtiError("bad_version")
    return platform, claims


async def use_nonce(db: AsyncSession, nonce: str) -> None:
    """A nonce works once (no replays); old ones are cleaned up as we go."""
    if not nonce:
        raise LtiError("bad_nonce")
    now = datetime.utcnow()
    await db.execute(delete(LtiNonce).where(LtiNonce.expires_at < now))
    if (await db.execute(select(LtiNonce).where(LtiNonce.nonce == nonce))).scalar_one_or_none():
        raise LtiError("replay")
    db.add(LtiNonce(nonce=nonce[:255], expires_at=now + timedelta(hours=2)))
    await db.flush()


# ---------------------------------------------------------------- roles and people

def course_role(roles: list[str]) -> Optional[str]:
    """LTI roles → who the person is in the subject: a permission template for a teacher, "student", or None (no
    role we know, e.g. a mentor — no membership).
        Administrator (course, institution or system)              → professor (all permissions)
        Instructor#TeachingAssistant, Instructor, ContentDeveloper → assistant
        Instructor#Grader                                           → lab (лаборант)
        Learner                                                     → student
    Moodle sends only Instructor / Learner (+ Administrator); the exact permissions of each teacher are set by the ALE
    admin (then they are locked, see enrol). Instructor gets the assistant's permissions, not all of them, because
    Moodle sends it for assistants too — final grades and grading rules are given on purpose, not by default."""
    roles = roles or []
    short = {r.rsplit("#", 1)[-1] for r in roles if r.startswith(ROLE_MEMBERSHIP)} | {r for r in roles if "#" not in r}
    if "Administrator" in short or ROLE_INST_ADMIN in roles or ROLE_SYS_ADMIN in roles:
        return "professor"
    if ROLE_GRADER in roles or "Grader" in short:
        return "lab"
    if ROLE_TA in roles or short & {"TeachingAssistant", "Instructor", "ContentDeveloper"}:
        return "assistant"
    if "Learner" in short:
        return "student"
    return None


def is_instructor(roles: list[str]) -> bool:
    return course_role(roles) in ("professor", "assistant", "lab")


def _placeholder_email(platform: LtiPlatform, sub: str) -> str:
    """When Moodle doesn't share the e-mail (privacy settings) the account still needs a unique address."""
    host = re.sub(r"^https?://", "", platform.issuer).split("/")[0].split(":")[0] or "lti"
    return f"{re.sub(r'[^a-zA-Z0-9._-]', '_', sub)[:60]}.{str(platform.id)[:8]}@{host}.lti.invalid"


async def user_for(db: AsyncSession, platform: LtiPlatform, sub: str, email: str, name: str,
                   instructor: bool) -> tuple[User, bool]:
    """The ALE account of a Moodle user: by the link from an earlier launch, else (when the platform allows it) by
    e-mail, else a new account. Returns (user, created)."""
    email = (email or "").strip().lower()
    link = (await db.execute(select(LtiUser).where(LtiUser.platform_id == platform.id, LtiUser.sub == sub))).scalar_one_or_none()
    user, created = None, False
    if link:
        user = await db.get(User, link.user_id)
    if user is None and email and platform.link_by_email:
        user = (await db.execute(select(User).where(func.lower(User.email) == email))).scalar_one_or_none()
    if user is None:
        addr = email or _placeholder_email(platform, sub)
        if (await db.execute(select(User).where(func.lower(User.email) == addr))).scalar_one_or_none():
            # the e-mail belongs to someone else and this platform may not link by e-mail
            raise LtiError("email_taken", addr)
        user = User(email=addr, name=(name or addr.split("@")[0])[:255], password_hash="!lti",
                    role="teacher" if instructor else "student", auth_provider="lti")
        db.add(user)
        await db.flush()
        created = True
        observability.log_event("lti_user_created", user_id=str(user.id))
    else:
        if instructor and user.role == "student":
            user.role = "teacher"  # a teacher in the faculty's Moodle
        if name and user.auth_provider == "lti" and user.name != name[:255]:
            user.name = name[:255]
    if created or (instructor and user.role == "teacher"):
        from app.services import spaces   # a new student: the spaces of their plan; a new teacher: none of those
        await db.flush()
        await spaces.sync_students(db, user.id)
    if link is None:
        db.add(LtiUser(platform_id=platform.id, sub=sub, user_id=user.id))
    elif link.user_id != user.id:
        link.user_id = user.id
    else:
        link.last_launch_at = datetime.utcnow()
    await db.flush()
    return user, created


async def enrol(db: AsyncSession, course_id, user: User, role: Optional[str]) -> Optional[str]:
    """Membership of the subject's space from Moodle's role (a template name or "student"). Moodle can raise what a
    person may do (student → teacher, more permissions), never lower it, and never changes a membership the ALE admin
    set (locked). Returns "teacher" / "student" — what the person is now."""
    if role is None:
        return None
    perms = [] if role == "student" else P.template(role)
    kind = "student" if role == "student" else "teacher"
    m = (await db.execute(select(CourseMember).where(CourseMember.course_id == course_id,
                                                     CourseMember.user_id == user.id))).scalar_one_or_none()
    if m is None:
        db.add(CourseMember(course_id=course_id, user_id=user.id, role=kind, permissions=perms, source="lti"))
        await db.flush()
        return kind
    if not m.role_locked and kind == "teacher":
        m.permissions = P.clean(set(m.permissions or []) | set(perms))
        m.role = "teacher"
    return m.role


# ---------------------------------------------------------------- service calls (AGS, NRPS)

_tokens: dict[tuple, tuple[str, float]] = {}


async def service_token(db: AsyncSession, platform: LtiPlatform, scopes: list[str]) -> str:
    """OAuth2 client_credentials with a JWT signed by ALE's key (private_key_jwt), cached until it expires."""
    key = (str(platform.id), " ".join(sorted(scopes)))
    if key in _tokens and _tokens[key][1] > time.time() + 30:
        return _tokens[key][0]
    now = int(time.time())
    assertion = await sign(db, {"iss": platform.client_id, "sub": platform.client_id, "aud": platform.auth_token_url,
                                "iat": now, "exp": now + 300, "jti": uuid.uuid4().hex})
    async with httpx.AsyncClient(timeout=15) as c:
        r = await c.post(platform.auth_token_url, data={
            "grant_type": "client_credentials",
            "client_assertion_type": "urn:ietf:params:oauth:client-assertion-type:jwt-bearer",
            "client_assertion": assertion, "scope": " ".join(scopes)})
    if r.status_code != 200 or "access_token" not in r.text:
        observability.log_event("lti_token_failed", status=r.status_code, body=r.text[:300])
        raise LtiError("service_token", f"{r.status_code}: {r.text[:200]}")
    data = r.json()
    _tokens[key] = (data["access_token"], time.time() + int(data.get("expires_in", 3600)))
    return data["access_token"]


def _with_path(url: str, suffix: str) -> str:
    """…/lineitem?type_id=1 + /scores → …/lineitem/scores?type_id=1 (the query string stays at the end)."""
    path, _, query = url.partition("?")
    return path.rstrip("/") + suffix + ("?" + query if query else "")


async def _call(db, platform, scopes, method, url, accept, json=None, content_type=None, params=None):
    tok = await service_token(db, platform, scopes)
    headers = {"Authorization": f"Bearer {tok}", "Accept": accept}
    if content_type:
        headers["Content-Type"] = content_type
    async with httpx.AsyncClient(timeout=20) as c:
        r = await c.request(method, url, headers=headers, json=json, params=params)
    if r.status_code >= 300:
        raise LtiError("service_failed", f"{method} {url} → {r.status_code}: {r.text[:200]}")
    return r


async def find_or_create_line_item(db, platform: LtiPlatform, ctx: LtiContext, resource_id: str, label: str,
                                   max_points: float) -> str:
    """A grade item in Moodle's gradebook for an ALE assignment (found by resourceId, made if missing)."""
    if not ctx.lineitems_url:
        raise LtiError("no_ags")
    r = await _call(db, platform, [SCOPE_LINEITEM], "GET", ctx.lineitems_url,
                    "application/vnd.ims.lis.v2.lineitemcontainer+json", params={"resource_id": resource_id})
    for it in r.json() or []:
        if str(it.get("resourceId")) == resource_id:
            return it["id"]
    r = await _call(db, platform, [SCOPE_LINEITEM], "POST", ctx.lineitems_url, "application/vnd.ims.lis.v2.lineitem+json",
                    json={"label": label[:250], "scoreMaximum": max_points or 1, "resourceId": resource_id, "tag": "ale"},
                    content_type="application/vnd.ims.lis.v2.lineitem+json")
    return r.json()["id"]


async def post_score(db, platform: LtiPlatform, lineitem_url: str, sub: str, given: float, maximum: float,
                     comment: str = "") -> None:
    body = {"userId": sub, "scoreGiven": max(0.0, round(given, 2)), "scoreMaximum": maximum or 1,
            "activityProgress": "Completed", "gradingProgress": "FullyGraded",
            "timestamp": datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")}
    if comment:
        body["comment"] = comment[:1000]
    await _call(db, platform, [SCOPE_SCORE], "POST", _with_path(lineitem_url, "/scores"),
                "application/json", json=body, content_type="application/vnd.ims.lis.v1.score+json")


async def members(db, platform: LtiPlatform, ctx: LtiContext) -> list[dict]:
    """Every participant of the Moodle course (all pages)."""
    if not ctx.memberships_url:
        raise LtiError("no_nrps")
    out, url, params = [], ctx.memberships_url, None
    for _ in range(50):
        r = await _call(db, platform, [SCOPE_NRPS], "GET", url, "application/vnd.ims.lti-nrps.v2.membershipcontainer+json",
                        params=params)
        out += r.json().get("members", [])
        m = re.search(r'<([^>]+)>;\s*rel="next"', r.headers.get("link", ""))
        if not m:
            break
        url, params = m.group(1), None
    return out
