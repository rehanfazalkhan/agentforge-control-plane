"""Domain models shared by the AgentForge control plane."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class RunStatus(str, Enum):
    COMPLETED = "completed"
    BLOCKED = "blocked"
    FAILED = "failed"


class ToolCall(BaseModel):
    name: str
    input: dict[str, Any]
    output: dict[str, Any]
    duration_ms: int = Field(ge=0)
    policy_decision: str


class TraceSpan(BaseModel):
    name: str
    kind: str
    duration_ms: int = Field(ge=0)
    attributes: dict[str, Any] = Field(default_factory=dict)


class EvaluationScore(BaseModel):
    name: str
    score: float = Field(ge=0, le=1)
    passed: bool
    rationale: str


class RunRequest(BaseModel):
    question: str = Field(min_length=3, max_length=1000)
    actor_role: str = Field(default="operator", pattern="^(operator|analyst|admin)$")


class AgentRun(BaseModel):
    id: str
    question: str
    actor_role: str
    created_at: datetime = Field(default_factory=utc_now)
    status: RunStatus
    route: str
    response: str
    citations: list[str] = Field(default_factory=list)
    tool_calls: list[ToolCall] = Field(default_factory=list)
    trace: list[TraceSpan] = Field(default_factory=list)
    evaluations: list[EvaluationScore] = Field(default_factory=list)
    latency_ms: int = Field(ge=0)


class Overview(BaseModel):
    total_runs: int
    success_rate: float
    average_latency_ms: int
    policy_blocks: int
    evaluation_pass_rate: float
