from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.config import settings
from app.database import AsyncSessionLocal
from app.routers import auth, tasks, sessions, admin, ops, courses, users, sso, assignments, profiles, emails, materials, standings, diagrams, ai_keys, subjects, lti, electives, logs
from app.services import ai_config, observability, reminders, submission_queue
from app.services.agent_service import AIUnavailable


@asynccontextmanager
async def lifespan(_: FastAPI):
    observability.setup_logging()
    try:
        cfg = await ai_config.load()
        observability.log_event("ai config loaded", provider=cfg.provider, model=cfg.model, source=cfg.source,
                                has_key=bool(cfg.api_key))
    except Exception:
        observability.log.exception("could not load AI settings; using environment defaults")
    gone = await observability.prune(settings.LOG_RETENTION_DAYS)
    if gone:
        observability.log_event("old logs pruned", events=gone, days=settings.LOG_RETENTION_DAYS)
    submission_queue.start()  # finish submissions an earlier run left in the queue
    reminders.start()  # deadline reminders, every few minutes
    yield


app = FastAPI(title="ALE - Adaptive Learning Environment", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID", "Content-Disposition"],
)
app.add_middleware(observability.RequestLogMiddleware)

app.include_router(auth.router)
app.include_router(tasks.router)
app.include_router(sessions.router)
app.include_router(admin.router)
app.include_router(ops.router)
app.include_router(courses.router)
app.include_router(users.router)
app.include_router(sso.router)
app.include_router(assignments.router)
app.include_router(profiles.router)
app.include_router(emails.router)
app.include_router(materials.router)
app.include_router(standings.router)
app.include_router(diagrams.router)
app.include_router(ai_keys.router)
app.include_router(subjects.router)
app.include_router(lti.router)
app.include_router(electives.router)
app.include_router(logs.router)


@app.exception_handler(AIUnavailable)
async def ai_unavailable(_: Request, __: AIUnavailable):
    return JSONResponse(status_code=503, content={"detail": "AI provider is not configured"})


@app.get("/health")
async def health():
    """Liveness + dependencies: database and code runner."""
    import httpx
    from app.config import settings

    checks = {}
    try:
        async with AsyncSessionLocal() as db:
            await db.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as e:
        checks["database"] = f"error: {type(e).__name__}"
    try:
        async with httpx.AsyncClient(timeout=3) as c:
            r = await c.get(f"{settings.CODE_RUNNER_URL}/health")
        checks["code_runner"] = "ok" if r.status_code == 200 else f"error: HTTP {r.status_code}"
    except Exception as e:
        checks["code_runner"] = f"error: {type(e).__name__}"
    checks["ai"] = "configured" if ai_config.platform().api_key else "not configured"
    ok = checks["database"] == "ok" and checks["code_runner"] == "ok"
    return JSONResponse(status_code=200 if ok else 503, content={"status": "ok" if ok else "degraded", **checks})
