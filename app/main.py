"""FastAPI entry point for the AgentForge control-plane dashboard."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .models import AgentRun, Overview, RunRequest
from .service import AgentForgeService
from .tools import TOOL_CATALOG

BASE_DIR = Path(__file__).resolve().parent.parent
service = AgentForgeService()

app = FastAPI(
    title="AgentForge Control Plane",
    version="0.1.0",
    description="Governed multi-agent orchestration with live traces and evaluation gates.",
)
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")


@app.get("/", include_in_schema=False)
def dashboard() -> FileResponse:
    return FileResponse(BASE_DIR / "static" / "index.html")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "agentforge-control-plane"}


@app.get("/ping")
def ping() -> dict[str, str]:
    """Health endpoint for an AgentCore Runtime-compatible container deployment."""
    return {"status": "Healthy"}


@app.get("/api/overview", response_model=Overview)
def overview() -> Overview:
    return service.overview()


@app.get("/api/tools")
def tools() -> list[dict[str, object]]:
    return TOOL_CATALOG


@app.get("/api/runs", response_model=list[AgentRun])
def runs() -> list[AgentRun]:
    return service.runs()


@app.get("/api/runs/{run_id}", response_model=AgentRun)
def get_run(run_id: str) -> AgentRun:
    for run in service.runs():
        if run.id == run_id:
            return run
    raise HTTPException(status_code=404, detail="Run not found")


@app.post("/api/runs", response_model=AgentRun, status_code=201)
def create_run(request: RunRequest) -> AgentRun:
    return service.run(request)


@app.post("/invocations", response_model=AgentRun)
def agentcore_invocation(payload: dict[str, str]) -> AgentRun:
    """Small HTTP adapter for a Runtime deployment; dashboard uses /api/runs."""
    prompt = payload.get("prompt") or payload.get("question")
    if not prompt:
        raise HTTPException(status_code=422, detail="Provide a 'prompt' or 'question'.")
    return service.run(RunRequest(question=prompt, actor_role=payload.get("actor_role", "operator")))
