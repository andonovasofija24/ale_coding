"""
ALE as an LTI 1.3 tool in the faculty's Moodle (courses.finki).

Moodle → ALE
  GET|POST /lti/login            OIDC third-party login initiation (step 1 of every launch)
  POST     /lti/launch           the signed launch (id_token): sign-in, course, role; also Deep Linking requests
  GET      /lti/jwks             ALE's public key (Moodle checks deep links and service tokens with it)
  GET      /lti/register?t=…     LTI Dynamic Registration: the Moodle admin pastes this one URL

The app (after a launch)
  GET  /lti/setup?s=…            first teacher launch from a Moodle course: link it to an ALE course or make one
  POST /lti/setup
  GET  /lti/deeplink?d=…         "Select content" in Moodle: which ALE assignment(s) to place in the Moodle course
  POST /lti/deeplink             → the signed response the app posts back to Moodle

Course staff
  GET    /courses/{id}/lti                 linked Moodle courses
  POST   /courses/{id}/lti/roster          participants from Moodle (Names and Role Provisioning)
  POST   /courses/{id}/lti/grades          points to Moodle's gradebook (Assignment and Grade Services)
  DELETE /courses/{id}/lti/{context_id}    unlink

Admin
  GET  /admin/lti                          the tool's URLs and key for Moodle, platforms, registration links
  POST /admin/lti/platforms   PUT|DELETE /admin/lti/platforms/{id}
  POST /admin/lti/registrations            a one-time dynamic-registration URL
"""
import html
import secrets
import time
import uuid
from datetime import datetime, timedelta
from typing import Optional
from urllib.parse import urlencode, urlparse

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from jose import jwt
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core import access
from app.core.deps import get_current_admin, get_current_user
from app.core.security import create_access_token
from app.database import AsyncSessionLocal, get_db
from app.models.course import Assignment, Course, CourseMember
from app.models.lti import LtiContext, LtiLineItem, LtiPlatform, LtiRegistration, LtiUser
from app.models.task import Subject
from app.models.user import User
from app.services import lti, observability
from app.services.lti import AGS_CLAIM, CLAIM, DL_CLAIM, NRPS_CLAIM, LtiError

router = APIRouter(tags=["lti"])

HANDOFF_MINUTES = 30


def _frontend(path: str) -> str:
    return settings.FRONTEND_URL.rstrip("/") + path


def _handoff(kind: str, data: dict) -> str:
    """A short-lived signed note for the app (what to do after the launch); nothing secret is in it."""
    return jwt.encode({"k": kind, **data, "exp": int(time.time()) + HANDOFF_MINUTES * 60},
                      settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def _read_handoff(token: str, kind: str) -> dict:
    try:
        data = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except Exception:
        raise HTTPException(status_code=400, detail="lti.expired")
    if data.get("k") != kind:
        raise HTTPException(status_code=400, detail="lti.expired")
    return data


def _cookie_path() -> str:
    """/lti, or /api/lti when the backend is behind the bundled nginx (PUBLIC_URL …/api)."""
    return (urlparse(settings.PUBLIC_URL).path.rstrip("/") or "") + "/lti"


def _error_page(code: str, detail: str = "") -> RedirectResponse:
    observability.log_event("lti_failed", reason=code, detail=detail[:300])
    return RedirectResponse(_frontend("/lti?" + urlencode({"error": code})), status_code=303)


# ================================================================ Moodle → ALE

@router.get("/lti/jwks")
async def tool_jwks(db: AsyncSession = Depends(get_db)):
    return await lti.jwks(db)


@router.api_route("/lti/login", methods=["GET", "POST"])
async def oidc_login(request: Request, db: AsyncSession = Depends(get_db)):
    """Step 1: Moodle says who wants in; ALE sends the browser back to Moodle's auth endpoint with a state and nonce."""
    p = dict(request.query_params)
    if request.method == "POST":
        p.update({k: v for k, v in (await request.form()).items() if isinstance(v, str)})
    iss, hint = p.get("iss", ""), p.get("login_hint", "")
    if not iss or not hint:
        return _error_page("bad_login")
    try:
        platform = await lti.find_platform(db, iss, p.get("client_id"))
    except LtiError as e:
        return _error_page(e.code, e.detail)
    nonce = secrets.token_urlsafe(24)
    # The state carries the nonce, signed: the launch is checked against it even when the browser blocks
    # third-party cookies (Moodle often shows tools in an iframe). The cookie, when it arrives, is checked too.
    state = jwt.encode({"n": nonce, "p": str(platform.id), "exp": int(time.time()) + 600},
                       settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    params = {"scope": "openid", "response_type": "id_token", "response_mode": "form_post", "prompt": "none",
              "client_id": platform.client_id, "redirect_uri": lti.tool_urls()["launch"], "login_hint": hint,
              "state": state, "nonce": nonce}
    if p.get("lti_message_hint"):
        params["lti_message_hint"] = p["lti_message_hint"]
    r = RedirectResponse(platform.auth_login_url + ("&" if "?" in platform.auth_login_url else "?") + urlencode(params),
                         status_code=302)
    secure = settings.PUBLIC_URL.startswith("https://")
    r.set_cookie("ale_lti_state", nonce, max_age=600, httponly=True, path=_cookie_path(),
                 samesite="none" if secure else "lax", secure=secure)
    return r


@router.post("/lti/launch")
async def launch(request: Request, db: AsyncSession = Depends(get_db)):
    """Step 2: the signed launch. Signs the person in (making the account the first time), puts them in the ALE
    course linked to the Moodle course with Moodle's role, and opens the right page."""
    form = await request.form()
    if form.get("error"):
        return _error_page("platform_error", str(form.get("error_description") or form.get("error")))
    token, state = str(form.get("id_token") or ""), str(form.get("state") or "")
    try:
        st = jwt.decode(state, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except Exception:
        return _error_page("expired")
    try:
        platform, c = await lti.verify_id_token(db, token)
        if str(platform.id) != st.get("p") or c.get("nonce") != st.get("n"):
            raise LtiError("bad_nonce")
        cookie = request.cookies.get("ale_lti_state")
        if cookie and not secrets.compare_digest(cookie, st["n"]):
            raise LtiError("bad_nonce")
        await lti.use_nonce(db, c["nonce"])
        target = await _handle(db, platform, c)
        await db.commit()
    except LtiError as e:
        await db.rollback()
        return _error_page(e.code, e.detail)
    r = RedirectResponse(_frontend("/lti#" + urlencode(target)), status_code=303)
    r.delete_cookie("ale_lti_state", path=_cookie_path())
    return r


async def _handle(db: AsyncSession, platform: LtiPlatform, c: dict) -> dict:
    kind = c.get(CLAIM + "message_type")
    if kind not in ("LtiResourceLinkRequest", "LtiDeepLinkingRequest"):
        raise LtiError("bad_message", str(kind))
    sub = str(c.get("sub") or "")
    if not sub:
        raise LtiError("anonymous")  # Moodle didn't say who it is
    roles = c.get(CLAIM + "roles") or []
    course_role = lti.course_role(roles)
    name = c.get("name") or " ".join(x for x in (c.get("given_name"), c.get("family_name")) if x) or ""
    user, created = await lti.user_for(db, platform, sub, c.get("email", ""), name, lti.is_instructor(roles))
    out = {"token": create_access_token({"sub": str(user.id)})}
    if created:
        out["new"] = "1"

    context = c.get(CLAIM + "context") or {}
    ctx = None
    if context.get("id"):
        ctx = (await db.execute(select(LtiContext).where(LtiContext.platform_id == platform.id,
                                                         LtiContext.context_id == str(context["id"])))).scalar_one_or_none()
        if ctx is None:
            ctx = LtiContext(platform_id=platform.id, context_id=str(context["id"]))
            db.add(ctx)
        ctx.deployment_id = c.get(CLAIM + "deployment_id", "")
        ctx.label, ctx.title = str(context.get("label") or "")[:255], str(context.get("title") or "")[:500]
        ags, nrps = c.get(AGS_CLAIM) or {}, c.get(NRPS_CLAIM) or {}
        if ags.get("lineitems"):
            ctx.lineitems_url, ctx.ags_scopes = ags["lineitems"], ags.get("scope") or []
        if nrps.get("context_memberships_url"):
            ctx.memberships_url = nrps["context_memberships_url"]
        await db.flush()
        if ctx.course_id:
            await lti.enrol(db, ctx.course_id, user, course_role)

    if kind == "LtiDeepLinkingRequest":
        if course_role not in ("teacher", "assistant"):
            raise LtiError("not_instructor")
        dl = c.get(DL_CLAIM + "deep_linking_settings") or {}
        if not dl.get("deep_link_return_url"):
            raise LtiError("bad_message", "deep_link_return_url")
        out["deeplink"] = _handoff("dl", {
            "pl": str(platform.id), "ctx": str(ctx.id) if ctx else "", "ret": dl["deep_link_return_url"],
            "data": dl.get("data") or "", "dep": c.get(CLAIM + "deployment_id", ""),
            "multi": bool(dl.get("accept_multiple", True))})
        return out

    if ctx is None:
        out["next"] = "/courses"
        return out
    if ctx.course_id is None:
        if course_role in ("teacher", "assistant"):
            out["setup"] = _handoff("setup", {"ctx": str(ctx.id)})
            return out
        raise LtiError("course_not_ready")  # a student came before any teacher opened ALE from this course

    custom = c.get(CLAIM + "custom") or {}
    aid = str(custom.get("assignment_id") or "")
    next_path = f"/courses/{ctx.course_id}"
    if aid:
        a = (await db.execute(select(Assignment).where(Assignment.id == _uuid(aid),
                                                       Assignment.course_id == ctx.course_id))).scalar_one_or_none()
        if a:
            next_path = f"/assignments/{a.id}"
            lineitem = (c.get(AGS_CLAIM) or {}).get("lineitem")
            if lineitem:  # the grade item Moodle made for this activity: its points go there
                li = (await db.execute(select(LtiLineItem).where(LtiLineItem.context_id == ctx.id,
                                                                 LtiLineItem.assignment_id == a.id))).scalar_one_or_none()
                if li is None:
                    db.add(LtiLineItem(context_id=ctx.id, assignment_id=a.id, url=lineitem))
                elif li.url != lineitem:
                    li.url = lineitem
    out["next"] = next_path
    return out


def _uuid(s: str):
    try:
        return uuid.UUID(s)
    except ValueError:
        return uuid.UUID(int=0)


# ---------------------------------------------------------------- dynamic registration

def _close_page(ok: bool, message: str) -> HTMLResponse:
    """Shown inside Moodle's registration dialog; tells Moodle to close it."""
    color = "#2F9E44" if ok else "#E03131"
    return HTMLResponse(f"""<!doctype html><html><head><meta charset="utf-8"><title>ALE</title></head>
<body style="font-family:system-ui,sans-serif;padding:32px;color:#1A2233">
<p style="font-weight:800;font-size:20px;color:{color}">{'✓' if ok else '✗'} ALE</p><p>{html.escape(message)}</p>
<script>setTimeout(function(){{(window.opener||window.parent).postMessage({{subject:'org.imsglobal.lti.close'}},'*')}}, {1500 if ok else 8000});</script>
</body></html>""", status_code=200 if ok else 400)


@router.get("/lti/register")
async def dynamic_registration(t: str, openid_configuration: str, registration_token: str = "",
                               db: AsyncSession = Depends(get_db)):
    reg = await db.get(LtiRegistration, t)
    if reg is None or reg.used_at or reg.expires_at < datetime.utcnow():
        return _close_page(False, "This registration link is not valid any more. Make a new one in ALE (Administration → LTI).")
    try:
        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.get(openid_configuration)
            r.raise_for_status()
            conf = r.json()
            issuer = conf["issuer"].rstrip("/")
            # the configuration must come from the platform it describes
            if urlparse(openid_configuration).netloc != urlparse(issuer).netloc:
                raise ValueError("issuer and configuration URL differ")
            u = lti.tool_urls()
            body = {
                "application_type": "web", "response_types": ["id_token"], "grant_types": ["implicit", "client_credentials"],
                "initiate_login_uri": u["login"], "redirect_uris": [u["launch"]], "client_name": "ALE",
                "jwks_uri": u["jwks"], "token_endpoint_auth_method": "private_key_jwt",
                "scope": " ".join(lti.ALL_SCOPES),
                lti.TOOL_CONFIG: {
                    "domain": u["domain"], "target_link_uri": u["launch"],
                    "description": "ALE — Adaptive Learning Environment: programming tasks with tests and an AI tutor",
                    "claims": ["iss", "sub", "name", "given_name", "family_name", "email"],
                    "messages": [{"type": "LtiDeepLinkingRequest", "target_link_uri": u["launch"], "label": "ALE"}],
                },
            }
            headers = {"Authorization": f"Bearer {registration_token}"} if registration_token else {}
            r2 = await c.post(conf["registration_endpoint"], json=body, headers=headers)
            r2.raise_for_status()
            res = r2.json()
    except Exception as e:
        observability.log_event("lti_register_failed", error=f"{type(e).__name__}: {e}"[:300])
        return _close_page(False, f"Registration failed: {type(e).__name__}: {str(e)[:200]}")
    dep = (res.get(lti.TOOL_CONFIG) or {}).get("deployment_id")
    platform = (await db.execute(select(LtiPlatform).where(LtiPlatform.issuer == issuer,
                                                           LtiPlatform.client_id == res["client_id"]))).scalar_one_or_none()
    if platform is None:
        platform = LtiPlatform(issuer=issuer, client_id=res["client_id"], name=reg.name,
                               auth_login_url=conf["authorization_endpoint"], auth_token_url=conf["token_endpoint"],
                               jwks_url=conf["jwks_uri"], deployment_ids=[str(dep)] if dep else [])
        db.add(platform)
    await db.flush()
    reg.used_at, reg.platform_id = datetime.utcnow(), platform.id
    await db.commit()
    observability.log_event("lti_registered", issuer=issuer)
    return _close_page(True, "ALE is registered. Activate the tool in Moodle (Manage tools) and it is ready.")


# ================================================================ the app, after a launch

class SetupIn(BaseModel):
    s: str
    course_id: Optional[uuid.UUID] = None   # link to this course; None = make a new one from the Moodle course


async def _setup_context(db, user: User, s: str) -> LtiContext:
    data = _read_handoff(s, "setup")
    ctx = await db.get(LtiContext, _uuid(data["ctx"]))
    if ctx is None:
        raise HTTPException(status_code=404, detail="lti.expired")
    return ctx


@router.get("/lti/setup")
async def setup_info(s: str, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    ctx = await _setup_context(db, user, s)
    mine = (await db.execute(select(Course).join(CourseMember, CourseMember.course_id == Course.id)
                             .where(CourseMember.user_id == user.id, CourseMember.role.in_(access.COURSE_STAFF),
                                    Course.archived.is_(False)).order_by(Course.created_at.desc()))).scalars().all()
    if user.role == "admin":
        mine = (await db.execute(select(Course).where(Course.archived.is_(False)).order_by(Course.created_at.desc()))).scalars().all()
    linked = {r for (r,) in (await db.execute(select(LtiContext.course_id).where(LtiContext.course_id.is_not(None)))).all()}
    subject = await _guess_subject(db, ctx)
    return {"label": ctx.label, "title": ctx.title, "course_id": str(ctx.course_id) if ctx.course_id else None,
            "subject": {"id": str(subject.id), "code": subject.code, "name": subject.name} if subject else None,
            # a course of the same subject first: most likely the one this Moodle course is a run of
            "courses": sorted([{"id": str(x.id), "code": x.code, "name": x.name, "semester": x.semester,
                                "linked": x.id in linked, "suggested": _same_course(x, subject, ctx)}
                               for x in mine], key=lambda c: not c["suggested"])}


def _same_course(course: Course, subject: Optional[Subject], ctx: LtiContext) -> bool:
    """Is this ALE course probably a run of the same thing as the Moodle course (same subject, or same name)?"""
    if subject and course.subject_id == subject.id:
        return True
    name = course.name.strip().lower()
    return bool(name) and (name in f"{ctx.title} {ctx.label}".lower() or bool(subject and name == subject.name.lower()))


async def _guess_subject(db, ctx: LtiContext) -> Optional[Subject]:
    title = f"{ctx.title} {ctx.label}".lower()
    best = None
    for s in (await db.execute(select(Subject))).scalars().all():
        names = [n.lower() for n in (s.name, s.name_en) if n]
        if any(n in title for n in names) and (best is None or len(s.name) > len(best.name)):
            best = s
    return best


@router.post("/lti/setup")
async def setup(body: SetupIn, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    ctx = await _setup_context(db, user, body.s)
    if ctx.course_id:
        return {"course_id": str(ctx.course_id)}
    if body.course_id:
        course, _ = await access.load_course(db, user, body.course_id, ("teacher",))
    else:
        access.require_admin(user)  # only the administrator makes courses
        subject = await _guess_subject(db, ctx)
        from app.routers.courses import _new_join_code
        course = Course(code=(ctx.label or "LTI")[:50], name=(ctx.title or ctx.label or "Moodle")[:300],
                        join_code=_new_join_code(), created_by=user.id, subject_id=subject.id if subject else None)
        db.add(course)
        await db.flush()
        db.add(CourseMember(course_id=course.id, user_id=user.id, role="teacher"))
    ctx.course_id = course.id
    await lti.enrol(db, course.id, user, "teacher")
    await db.commit()
    observability.log_event("lti_context_linked", course_id=str(course.id))
    return {"course_id": str(course.id)}


class DeepLinkIn(BaseModel):
    d: str
    assignment_ids: list[uuid.UUID] = Field(default_factory=list, max_length=50)
    course_link: bool = False      # also (or only) a link to the whole course


@router.get("/lti/deeplink")
async def deeplink_info(d: str, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    data = _read_handoff(d, "dl")
    ctx = await db.get(LtiContext, _uuid(data["ctx"])) if data.get("ctx") else None
    out = {"label": ctx.label if ctx else "", "title": ctx.title if ctx else "", "multiple": data.get("multi", True),
           "course": None, "assignments": [],
           "setup": _handoff("setup", {"ctx": str(ctx.id)}) if ctx and not ctx.course_id else None}
    if ctx and ctx.course_id:
        course, _ = await access.load_course(db, user, ctx.course_id, access.COURSE_STAFF)
        rows = (await db.execute(select(Assignment).where(Assignment.course_id == course.id)
                                 .order_by(Assignment.due_at.is_(None), Assignment.due_at, Assignment.created_at))).scalars().all()
        out["course"] = {"id": str(course.id), "code": course.code, "name": course.name}
        out["assignments"] = [{"id": str(a.id), "title": a.title, "kind": a.kind, "published": a.published,
                               "due_at": a.due_at.isoformat() + "Z" if a.due_at else None} for a in rows]
    return out


@router.post("/lti/deeplink")
async def deeplink(body: DeepLinkIn, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    """The signed Deep Linking response: Moodle adds one activity per chosen assignment (each with its own grade
    item), and/or a link to the course."""
    from app.services import exam
    data = _read_handoff(body.d, "dl")
    platform = await db.get(LtiPlatform, _uuid(data["pl"]))
    ctx = await db.get(LtiContext, _uuid(data["ctx"])) if data.get("ctx") else None
    if platform is None or ctx is None or ctx.course_id is None:
        raise HTTPException(status_code=400, detail="lti.notLinked")
    course, _ = await access.load_course(db, user, ctx.course_id, access.COURSE_STAFF)
    launch_url = lti.tool_urls()["launch"]
    items = []
    if body.course_link:
        items.append({"type": "ltiResourceLink", "title": f"ALE — {course.name}", "url": launch_url,
                      "text": "Задачи, лабораториски и домашни во ALE"})
    for aid in body.assignment_ids:
        a = (await db.execute(select(Assignment).where(Assignment.id == aid, Assignment.course_id == course.id))).scalar_one_or_none()
        if a is None:
            continue
        from app.routers.assignments import _task_rows
        maxp = exam.max_points([at for at, _ in await _task_rows(db, a)])
        items.append({"type": "ltiResourceLink", "title": a.title, "url": launch_url,
                      "custom": {"assignment_id": str(a.id)},
                      "lineItem": {"label": a.title[:250], "scoreMaximum": maxp or 1, "resourceId": str(a.id), "tag": "ale"}})
    if not items:
        raise HTTPException(status_code=422, detail="lti.nothingChosen")
    if not data.get("multi", True):
        items = items[:1]
    now = int(time.time())
    claims = {"iss": platform.client_id, "aud": platform.issuer, "iat": now, "exp": now + 600,
              "nonce": secrets.token_urlsafe(16), CLAIM + "message_type": "LtiDeepLinkingResponse",
              CLAIM + "version": "1.3.0", CLAIM + "deployment_id": data.get("dep", ""),
              DL_CLAIM + "content_items": items}
    if data.get("data"):
        claims[DL_CLAIM + "data"] = data["data"]
    return {"return_url": data["ret"], "jwt": await lti.sign(db, claims), "count": len(items)}


# ================================================================ course staff: roster and grades

async def _contexts(db, course_id) -> list[tuple[LtiContext, LtiPlatform]]:
    return (await db.execute(select(LtiContext, LtiPlatform).join(LtiPlatform, LtiPlatform.id == LtiContext.platform_id)
                             .where(LtiContext.course_id == course_id))).all()


def _ctx_out(ctx: LtiContext, p: LtiPlatform) -> dict:
    return {"id": str(ctx.id), "platform": p.name, "issuer": p.issuer, "label": ctx.label, "title": ctx.title,
            "roster": bool(ctx.memberships_url), "grades": bool(ctx.lineitems_url) and lti.SCOPE_SCORE in (ctx.ags_scopes or []),
            "last_roster_sync": ctx.last_roster_sync.isoformat() + "Z" if ctx.last_roster_sync else None,
            "last_grade_sync": ctx.last_grade_sync.isoformat() + "Z" if ctx.last_grade_sync else None}


@router.get("/courses/{course_id}/lti")
async def course_lti(course_id: uuid.UUID, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    await access.load_course(db, user, course_id, access.COURSE_STAFF)
    return {"contexts": [_ctx_out(c, p) for c, p in await _contexts(db, course_id)]}


@router.delete("/courses/{course_id}/lti/{context_id}", status_code=204)
async def unlink(course_id: uuid.UUID, context_id: uuid.UUID, db: AsyncSession = Depends(get_db),
                 user: User = Depends(get_current_user)):
    await access.load_course(db, user, course_id, ("teacher",))
    ctx = await db.get(LtiContext, context_id)
    if ctx is None or ctx.course_id != course_id:
        raise HTTPException(status_code=404, detail="Not found")
    ctx.course_id = None
    for li in (await db.execute(select(LtiLineItem).where(LtiLineItem.context_id == ctx.id))).scalars().all():
        await db.delete(li)
    await db.commit()


@router.post("/courses/{course_id}/lti/roster")
async def sync_roster(course_id: uuid.UUID, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    """Everyone in the Moodle course gets an ALE account (if needed) and a place in this course with their role.
    Nobody is removed: a person who left the Moodle course is only reported."""
    await access.load_course(db, user, course_id, access.COURSE_STAFF)
    added, updated, skipped, left = 0, 0, 0, 0
    for ctx, platform in await _contexts(db, course_id):
        try:
            people = await lti.members(db, platform, ctx)
        except LtiError as e:
            raise HTTPException(status_code=502, detail=f"lti.{e.code}")
        for m in people:
            if m.get("status") in ("Inactive", "Deleted"):
                left += 1
                continue
            role = lti.course_role(m.get("roles") or [])
            if role is None or not m.get("user_id"):
                skipped += 1
                continue
            before = await _member_role(db, course_id, m, platform)
            try:
                person, _ = await lti.user_for(db, platform, str(m["user_id"]), m.get("email", ""),
                                               m.get("name") or " ".join(x for x in (m.get("given_name"), m.get("family_name")) if x),
                                               role in ("teacher", "assistant"))
            except LtiError:
                skipped += 1
                continue
            now = await lti.enrol(db, course_id, person, role)
            if before is None:
                added += 1
            elif before != now:
                updated += 1
        ctx.last_roster_sync = datetime.utcnow()
    await db.commit()
    observability.log_event("lti_roster_synced", course_id=str(course_id), added=added)
    return {"added": added, "updated": updated, "skipped": skipped, "left": left}


async def _member_role(db, course_id, m: dict, platform: LtiPlatform) -> Optional[str]:
    row = (await db.execute(select(CourseMember.role).join(LtiUser, LtiUser.user_id == CourseMember.user_id)
                            .where(CourseMember.course_id == course_id, LtiUser.platform_id == platform.id,
                                   LtiUser.sub == str(m.get("user_id"))))).first()
    return row[0] if row else None


class GradesIn(BaseModel):
    assignment_id: Optional[uuid.UUID] = None   # None = every assignment whose points students may already see


async def push_grades(db: AsyncSession, course_id, only: Optional[uuid.UUID] = None) -> dict:
    """Points of the course's assignments → Moodle's gradebook. Only assignments that are published and whose
    points students may see (no "after publishing" hold, or already published); students without a Moodle
    account link are skipped."""
    from app.routers.assignments import gradebook_data
    contexts = await _contexts(db, course_id)
    if not contexts:
        return {"sent": 0, "items": 0, "skipped": 0, "assignments": 0}
    q = select(Assignment).where(Assignment.course_id == course_id, Assignment.published.is_(True))
    if only:
        q = q.where(Assignment.id == only)
    ready = {str(a.id): a for a in (await db.execute(q)).scalars().all()
             if not a.scores_after_publish or a.grades_published}
    if not ready:
        return {"sent": 0, "items": 0, "skipped": 0, "assignments": 0}
    book = await gradebook_data(db, course_id)
    maxp = {x["id"]: x["max_points"] for x in book["assignments"]}
    sent = skipped = items = 0
    for ctx, platform in contexts:
        if not ctx.lineitems_url and not (await db.execute(select(LtiLineItem.id).where(LtiLineItem.context_id == ctx.id))).first():
            continue
        subs = {str(u): s for u, s in (await db.execute(select(LtiUser.user_id, LtiUser.sub)
                                                        .where(LtiUser.platform_id == platform.id))).all()}
        for aid, a in ready.items():
            todo = []
            for row in book["students"]:
                sc = row["scores"].get(aid) or {}
                sub = subs.get(row["user_id"])
                if sc.get("score") is None or not sc.get("applies", True) or not sub:
                    skipped += 1
                else:
                    todo.append((sub, sc["score"]))
            if not todo:
                continue  # nothing to send: no empty column is made in Moodle's gradebook
            li = (await db.execute(select(LtiLineItem).where(LtiLineItem.context_id == ctx.id,
                                                             LtiLineItem.assignment_id == a.id))).scalar_one_or_none()
            try:
                if li is None:
                    url = await lti.find_or_create_line_item(db, platform, ctx, aid, a.title, maxp.get(aid) or 1)
                    li = LtiLineItem(context_id=ctx.id, assignment_id=a.id, url=url)
                    db.add(li)
                    await db.flush()
                items += 1
                for sub, score in todo:
                    await lti.post_score(db, platform, li.url, sub, score, maxp.get(aid) or 1)
                    sent += 1
            except LtiError as e:
                observability.log_event("lti_grades_failed", course_id=str(course_id), error=e.detail[:300])
                raise
        ctx.last_grade_sync = datetime.utcnow()
    await db.commit()
    observability.log_event("lti_grades_sent", course_id=str(course_id), sent=sent)
    return {"sent": sent, "items": items, "skipped": skipped, "assignments": len(ready)}


@router.post("/courses/{course_id}/lti/grades")
async def sync_grades(course_id: uuid.UUID, body: GradesIn, db: AsyncSession = Depends(get_db),
                      user: User = Depends(get_current_user)):
    await access.load_course(db, user, course_id, access.COURSE_STAFF)
    try:
        return await push_grades(db, course_id, body.assignment_id)
    except LtiError as e:
        raise HTTPException(status_code=502, detail=f"lti.{e.code}")


async def push_grades_later(course_id, assignment_id) -> None:
    """After "Publish grades": send them to Moodle in the background (a failure only shows in monitoring)."""
    async with AsyncSessionLocal() as db:
        try:
            await push_grades(db, course_id, assignment_id)
        except Exception as e:  # noqa: BLE001 — never breaks publishing
            observability.log_event("lti_grades_failed", course_id=str(course_id), error=f"{type(e).__name__}: {e}"[:300])


# ================================================================ admin

class PlatformIn(BaseModel):
    name: str = Field("Moodle", max_length=200)
    issuer: str = Field(..., min_length=8, max_length=500)
    client_id: str = Field(..., min_length=1, max_length=200)
    deployment_ids: list[str] = Field(default_factory=list, max_length=20)
    auth_login_url: str = Field("", max_length=500)
    auth_token_url: str = Field("", max_length=500)
    jwks_url: str = Field("", max_length=500)
    link_by_email: bool = True
    active: bool = True


def _platform_out(p: LtiPlatform) -> dict:
    return {"id": str(p.id), "name": p.name, "issuer": p.issuer, "client_id": p.client_id,
            "deployment_ids": p.deployment_ids, "auth_login_url": p.auth_login_url, "auth_token_url": p.auth_token_url,
            "jwks_url": p.jwks_url, "link_by_email": p.link_by_email, "active": p.active}


def _fill_moodle_defaults(body: PlatformIn) -> PlatformIn:
    """For a Moodle only the address is needed: its LTI endpoints are always at the same paths."""
    root = body.issuer.rstrip("/")
    body.issuer = root
    body.auth_login_url = body.auth_login_url or root + "/mod/lti/auth.php"
    body.auth_token_url = body.auth_token_url or root + "/mod/lti/token.php"
    body.jwks_url = body.jwks_url or root + "/mod/lti/certs.php"
    body.deployment_ids = [d.strip() for d in body.deployment_ids if d.strip()]
    return body


@router.get("/admin/lti")
async def admin_lti(db: AsyncSession = Depends(get_db), admin: User = Depends(get_current_admin)):
    key = await lti.tool_key(db)
    platforms = (await db.execute(select(LtiPlatform).order_by(LtiPlatform.created_at))).scalars().all()
    regs = (await db.execute(select(LtiRegistration).where(LtiRegistration.used_at.is_(None),
                                                           LtiRegistration.expires_at > datetime.utcnow()))).scalars().all()
    counts = {}
    for p in platforms:
        counts[str(p.id)] = {
            "users": len((await db.execute(select(LtiUser.id).where(LtiUser.platform_id == p.id))).all()),
            "courses": len((await db.execute(select(LtiContext.id).where(LtiContext.platform_id == p.id,
                                                                        LtiContext.course_id.is_not(None)))).all())}
    return {"tool": {**lti.tool_urls(), "public_jwk": key.public_jwk},
            "platforms": [{**_platform_out(p), **counts[str(p.id)]} for p in platforms],
            "registrations": [{"url": _reg_url(r.token), "name": r.name, "expires_at": r.expires_at.isoformat() + "Z"} for r in regs]}


def _reg_url(token: str) -> str:
    return lti.base() + "/lti/register?t=" + token


@router.post("/admin/lti/platforms", status_code=201)
async def add_platform(body: PlatformIn, db: AsyncSession = Depends(get_db), admin: User = Depends(get_current_admin)):
    body = _fill_moodle_defaults(body)
    if (await db.execute(select(LtiPlatform).where(LtiPlatform.issuer == body.issuer,
                                                   LtiPlatform.client_id == body.client_id))).scalar_one_or_none():
        raise HTTPException(status_code=409, detail="lti.platformExists")
    p = LtiPlatform(**body.model_dump())
    db.add(p)
    await db.commit()
    return _platform_out(p)


@router.put("/admin/lti/platforms/{platform_id}")
async def update_platform(platform_id: uuid.UUID, body: PlatformIn, db: AsyncSession = Depends(get_db),
                          admin: User = Depends(get_current_admin)):
    p = await db.get(LtiPlatform, platform_id)
    if p is None:
        raise HTTPException(status_code=404, detail="Not found")
    for k, v in _fill_moodle_defaults(body).model_dump().items():
        setattr(p, k, v)
    await db.commit()
    return _platform_out(p)


@router.delete("/admin/lti/platforms/{platform_id}", status_code=204)
async def delete_platform(platform_id: uuid.UUID, db: AsyncSession = Depends(get_db), admin: User = Depends(get_current_admin)):
    p = await db.get(LtiPlatform, platform_id)
    if p is None:
        raise HTTPException(status_code=404, detail="Not found")
    await db.delete(p)
    await db.commit()


class RegistrationIn(BaseModel):
    name: str = Field("courses.finki", max_length=200)


@router.post("/admin/lti/registrations", status_code=201)
async def new_registration(body: RegistrationIn, db: AsyncSession = Depends(get_db), admin: User = Depends(get_current_admin)):
    r = LtiRegistration(token=secrets.token_urlsafe(24), name=body.name.strip() or "Moodle",
                        expires_at=datetime.utcnow() + timedelta(days=7), created_by=admin.id)
    db.add(r)
    await db.commit()
    return {"url": _reg_url(r.token), "expires_at": r.expires_at.isoformat() + "Z"}
