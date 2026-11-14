"""
Sign in with Microsoft (Entra ID / Office 365 — the faculty accounts), standard OpenID Connect:
authorization-code flow with PKCE, the id_token's signature checked against Microsoft's published keys.

Enabled when MS_CLIENT_ID and MS_CLIENT_SECRET are set. In the Azure app registration add the redirect URI
    {PUBLIC_URL}/auth/microsoft/callback          e.g. http://localhost:8000/auth/microsoft/callback
New accounts are students; an admin can change the role. MS_ALLOWED_DOMAINS limits who may sign in
(e.g. "students.finki.ukim.mk,finki.ukim.mk").
"""
import base64
import hashlib
import secrets
import time
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from jose import jwt
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core import accounts
from app.core.security import create_access_token
from app.database import get_db
from app.models.user import User
from app.services import observability

router = APIRouter(prefix="/auth/microsoft", tags=["auth"])

COOKIE = "ale_sso"
_cache: dict = {}  # discovery document and signing keys, refreshed every hour


def enabled() -> bool:
    return bool(settings.MS_CLIENT_ID and settings.MS_CLIENT_SECRET)


def _authority() -> str:
    return (settings.MS_AUTHORITY or f"https://login.microsoftonline.com/{settings.MS_TENANT_ID}/v2.0").rstrip("/")


def _redirect_uri() -> str:
    return settings.PUBLIC_URL.rstrip("/") + "/auth/microsoft/callback"


async def _get_json(url: str) -> dict:
    async with httpx.AsyncClient(timeout=10) as c:
        r = await c.get(url)
        r.raise_for_status()
        return r.json()


async def _discovery() -> dict:
    if "disc" not in _cache or _cache["disc"][1] < time.time():
        _cache["disc"] = (await _get_json(_authority() + "/.well-known/openid-configuration"), time.time() + 3600)
    return _cache["disc"][0]


async def _jwks(force: bool = False) -> dict:
    if force or "jwks" not in _cache or _cache["jwks"][1] < time.time():
        _cache["jwks"] = (await _get_json((await _discovery())["jwks_uri"]), time.time() + 3600)
    return _cache["jwks"][0]


def _frontend(path: str) -> str:
    return settings.FRONTEND_URL.rstrip("/") + path


def _fail(code: str) -> RedirectResponse:
    observability.log_event("sso_failed", reason=code)
    r = RedirectResponse(_frontend(f"/login?sso_error={code}"), status_code=302)
    r.delete_cookie(COOKIE, path="/auth/microsoft")
    return r


@router.get("/config")
async def sso_config():
    return {"enabled": enabled()}


@router.get("/login")
async def sso_login():
    if not enabled():
        return _fail("disabled")
    try:
        disc = await _discovery()
    except Exception:
        return _fail("unavailable")
    state, nonce, verifier = secrets.token_urlsafe(24), secrets.token_urlsafe(24), secrets.token_urlsafe(48)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    params = {
        "client_id": settings.MS_CLIENT_ID, "response_type": "code", "redirect_uri": _redirect_uri(),
        "response_mode": "query", "scope": "openid profile email", "state": state, "nonce": nonce,
        "code_challenge": challenge, "code_challenge_method": "S256", "prompt": "select_account",
    }
    # The verifier and nonce stay in a short-lived, signed, HttpOnly cookie — never in the URL.
    cookie = jwt.encode({"state": state, "nonce": nonce, "verifier": verifier, "exp": int(time.time()) + 600},
                        settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    r = RedirectResponse(disc["authorization_endpoint"] + "?" + urlencode(params), status_code=302)
    r.set_cookie(COOKIE, cookie, max_age=600, httponly=True, samesite="lax", path="/auth/microsoft",
                 secure=settings.PUBLIC_URL.startswith("https://"))
    return r


def _check_issuer(claims: dict) -> bool:
    """Microsoft's issuer contains the tenant id: https://login.microsoftonline.com/{tid}/v2.0.
    With a fixed tenant (a GUID or domain in MS_TENANT_ID that resolved to one) the token must come from it."""
    tid, iss = claims.get("tid", ""), claims.get("iss", "")
    if settings.MS_AUTHORITY:  # custom / test authority: exact issuer from discovery
        return iss == _cache["disc"][0].get("issuer", "").replace("{tenantid}", tid)
    if iss != f"https://login.microsoftonline.com/{tid}/v2.0":
        return False
    fixed = settings.MS_TENANT_ID not in ("common", "organizations", "consumers")
    return not fixed or settings.MS_TENANT_ID == tid or not _looks_like_guid(settings.MS_TENANT_ID)


def _single_tenant() -> bool:
    """Locked to one tenant (MS_TENANT_ID is the faculty's tenant GUID), or a custom authority (tests)."""
    return bool(settings.MS_AUTHORITY) or _looks_like_guid(settings.MS_TENANT_ID)


def _looks_like_guid(s: str) -> bool:
    return len(s) == 36 and s.count("-") == 4


@router.get("/callback")
async def sso_callback(request: Request, db: AsyncSession = Depends(get_db)):
    q = request.query_params
    if q.get("error"):
        return _fail("cancelled" if q.get("error") == "access_denied" else "provider")
    raw = request.cookies.get(COOKIE)
    try:
        saved = jwt.decode(raw or "", settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except Exception:
        return _fail("expired")
    if not q.get("code") or not secrets.compare_digest(q.get("state", ""), saved["state"]):
        return _fail("state")

    try:
        disc = await _discovery()
        async with httpx.AsyncClient(timeout=15) as c:
            tr = await c.post(disc["token_endpoint"], data={
                "client_id": settings.MS_CLIENT_ID, "client_secret": settings.MS_CLIENT_SECRET,
                "grant_type": "authorization_code", "code": q["code"], "redirect_uri": _redirect_uri(),
                "code_verifier": saved["verifier"], "scope": "openid profile email",
            })
        if tr.status_code != 200:
            return _fail("token")
        id_token = tr.json().get("id_token", "")
        header = jwt.get_unverified_header(id_token)
        keys = await _jwks()
        if not any(k.get("kid") == header.get("kid") for k in keys.get("keys", [])):
            keys = await _jwks(force=True)  # Microsoft rotates its keys
        claims = jwt.decode(id_token, keys, algorithms=["RS256"], audience=settings.MS_CLIENT_ID,
                            options={"verify_at_hash": False})
    except Exception as e:
        observability.log_event("sso_token_invalid", error=f"{type(e).__name__}: {e}"[:300])
        return _fail("token")

    if claims.get("nonce") != saved["nonce"] or not _check_issuer(claims):
        return _fail("token")
    email = (claims.get("email") or claims.get("preferred_username") or "").strip().lower()
    if "@" not in email:
        return _fail("email")
    allowed = [d.strip().lower() for d in settings.MS_ALLOWED_DOMAINS.split(",") if d.strip()]
    if allowed and email.rsplit("@", 1)[1] not in allowed:
        return _fail("domain")

    user = (await db.execute(select(User).where(func.lower(User.email) == email))).scalar_one_or_none()
    if user is not None and user.auth_provider == "password" and not _single_tenant():
        # With "any organization" accounts, another tenant's admin could put any e-mail in the token, so an
        # existing password account is only taken over when the app is locked to the faculty's own tenant.
        return _fail("exists")
    if user is None:
        kind = accounts.account_for_email(email)
        if kind is None:   # the account type comes from the e-mail; other domains may not sign up
            return _fail("domain")
        user = User(email=email, name=(claims.get("name") or email.split("@")[0])[:255],
                    password_hash="!microsoft",  # not a valid hash: password login is impossible
                    role=kind, auth_provider="microsoft")
        db.add(user)
        await db.flush()
        from app.services import spaces
        await spaces.sync_students(db, user.id)    # a student: the spaces of their study plan
        await db.commit()
        await db.refresh(user)
        observability.log_event("sso_user_created", user_id=str(user.id))
    # The token goes to the app in the URL fragment: fragments are not sent to servers or written to logs.
    r = RedirectResponse(_frontend("/auth/callback#token=" + create_access_token({"sub": str(user.id)})), status_code=302)
    r.delete_cookie(COOKIE, path="/auth/microsoft")
    return r
