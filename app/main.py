"""FastAPI entry point with production authentication and AgentCore-compatible routes."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Header, HTTPException, Request, Response
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .auth import AuthenticationError, authenticate
from .models import AgentRun, Overview, RunRequest
from .service import AgentForgeService
from .tools import TOOL_CATALOG

BASE_DIR = Path(__file__).resolve().parent.parent
service = AgentForgeService()

app = FastAPI(
    title="AgentForge Control Plane",
    version="1.0.0",
    description="A production-grade governed multi-agent control plane with Bedrock, policy enforcement, and auditability.",
)
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Cache-Control"] = "no-store" if request.url.path.startswith("/api/") else "public, max-age=300"
    return response


def request_principal(request: RunRequest, authorization: str | None):
    try:
        return authenticate(authorization, service.settings, request.actor_role)
    except AuthenticationError as error:
        raise HTTPException(status_code=401, detail=str(error)) from error


@app.get("/", include_in_schema=False)
def dashboard() -> FileResponse:
    return FileResponse(BASE_DIR / "static" / "index.html")


@app.get("/health")
def health() -> dict[str, object]:
    return {"status": "ok", "service": "agentforge-control-plane", **service.readiness()}


@app.get("/readyz")
def readyz(response: Response) -> dict[str, object]:
    readiness = service.readiness()
    if not readiness["ready"]:
        response.status_code = 503
    return readiness


@app.get("/ping")
def ping() -> dict[str, str]:
    """Health endpoint for an AgentCore Runtime HTTP deployment."""
    return {"status": "Healthy"}


@app.get("/api/overview", response_model=Overview)
def overview() -> Overview:
    return service.overview()


@app.get("/api/tools")
def tools() -> list[dict[str, object]]:
    return [{key: value for key, value in tool.items() if key != "input_schema"} for tool in TOOL_CATALOG]


@app.get("/api/runs", response_model=list[AgentRun])
def runs() -> list[AgentRun]:
    return service.runs()


@app.get("/api/runs/{run_id}", response_model=AgentRun)
def get_run(run_id: str) -> AgentRun:
    run = service.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return run


@app.post("/api/runs", response_model=AgentRun, status_code=201)
def create_run(request: RunRequest, authorization: str | None = Header(default=None)) -> AgentRun:
    return service.run(request, request_principal(request, authorization))


@app.post("/invocations", response_model=AgentRun)
def agentcore_invocation(payload: dict[str, str], authorization: str | None = Header(default=None)) -> AgentRun:
    """AgentCore Runtime adapter. In production user identity comes from verified JWT claims."""
    prompt = payload.get("prompt") or payload.get("question")
    if not prompt:
        raise HTTPException(status_code=422, detail="Provide a 'prompt' or 'question'.")
    request = RunRequest(
        question=prompt,
        actor_role=payload.get("actor_role", "operator"),
        session_id=payload.get("session_id"),
    )
    return service.run(request, request_principal(request, authorization))
