import os
from fastapi import FastAPI, HTTPException, Request

from app.schemas import RunRequest, RunResponse
from app.runner import run_all

app = FastAPI(title="ALE Code Runner")

RUNNER_SECRET = os.getenv("RUNNER_SECRET", "runner_secret_change_me")


@app.middleware("http")
async def verify_secret(request: Request, call_next):
    if request.url.path == "/health":
        return await call_next(request)
    secret = request.headers.get("X-Runner-Secret")
    if secret != RUNNER_SECRET:
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=403, content={"detail": "Forbidden"})
    return await call_next(request)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/run", response_model=RunResponse)
def run(body: RunRequest):
    results = run_all(body.code, body.test_cases)
    return RunResponse(results=results)
