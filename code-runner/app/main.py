import os
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app import sandbox
from app.languages import available
from app.schemas import CheckRequest, CheckResponse, RunRequest, RunResponse
from app import check as checker
from app.runner import run_all

app = FastAPI(title="ALE Code Runner")

RUNNER_SECRET = os.getenv("RUNNER_SECRET", "runner_secret_change_me")


@app.middleware("http")
async def verify_secret(request: Request, call_next):
    if request.url.path == "/health":
        return await call_next(request)
    if request.headers.get("X-Runner-Secret") != RUNNER_SECRET:
        return JSONResponse(status_code=403, content={"detail": "Forbidden"})
    return await call_next(request)


@app.get("/health")
def health():
    """Liveness, queue state (how many submissions run now / wait) and the installed languages."""
    return {"status": "ok", **sandbox.stats(), "languages": _LANGS}


_LANGS = available()  # computed once: what is installed doesn't change while the runner runs


@app.post("/run", response_model=RunResponse)
def run(body: RunRequest):
    # Sync endpoint: FastAPI runs it in a worker thread, where it waits in the sandbox queue for a free slot.
    try:
        results = run_all(body.code, body.test_cases, body.language, body.reference_code)
    except sandbox.RunnerBusy:
        return JSONResponse(status_code=503, content={"detail": "Code runner is busy"}, headers={"Retry-After": "10"})
    return RunResponse(results=results)


@app.post("/check", response_model=CheckResponse)
def check(body: CheckRequest):
    """Compile only (never run) and return errors / warnings for the editor. Skipped when the runner is busy."""
    return checker.check(body.code, body.language, body.kind)
