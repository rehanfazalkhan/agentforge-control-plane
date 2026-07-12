"""Structured, CloudWatch-compatible audit events without prompt or secret logging."""

from __future__ import annotations

import json
import logging
from typing import Any

from .models import AgentRun


logger = logging.getLogger("agentforge.audit")


def emit(event: str, **attributes: Any) -> None:
    """Emit structured operational metadata; never add prompt or tool payload values here."""
    logger.info(json.dumps({"event": event, **attributes}, default=str, sort_keys=True))


def record_run(run: AgentRun) -> None:
    emit(
        "agent.run.completed",
        run_id=run.id,
        actor_id=run.actor_id,
        status=run.status.value,
        route=run.route,
        latency_ms=run.latency_ms,
        tool_count=len(run.tool_calls),
        evaluation_pass_rate=round(
            sum(score.passed for score in run.evaluations) / len(run.evaluations) * 100,
            1,
        ) if run.evaluations else 0,
        runtime_mode=run.runtime_mode,
    )
