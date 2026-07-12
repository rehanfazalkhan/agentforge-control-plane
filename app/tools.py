"""Deterministic MCP-style tool implementations used by the local demo."""

from __future__ import annotations

import time
from typing import Any

from .models import ToolCall
from .policy import authorize_tool


TOOL_CATALOG = [
    {
        "name": "get_service_health",
        "description": "Returns health and error rate for a named service.",
        "roles": ["operator", "analyst", "admin"],
    },
    {
        "name": "get_cost_forecast",
        "description": "Returns current-month cloud spend and a forecast.",
        "roles": ["analyst", "admin"],
    },
    {
        "name": "search_runbook",
        "description": "Finds approved operational runbook guidance.",
        "roles": ["operator", "analyst", "admin"],
    },
    {
        "name": "get_access_review",
        "description": "Lists privileged roles due for review.",
        "roles": ["admin"],
    },
]


def invoke_tool(actor_role: str, name: str, payload: dict[str, Any]) -> ToolCall:
    """Enforce policy before dispatching an allow-listed demo tool."""
    started = time.perf_counter()
    authorize_tool(actor_role, name)

    responses: dict[str, dict[str, Any]] = {
        "get_service_health": {
            "service": payload.get("service", "agent-runtime"),
            "status": "degraded",
            "error_rate": "2.1%",
            "p95_latency_ms": 840,
            "signal": "Elevated timeout errors began 18 minutes ago.",
        },
        "get_cost_forecast": {
            "month_to_date_usd": 18420,
            "forecast_usd": 23800,
            "budget_usd": 22000,
            "largest_driver": "Bedrock inference on customer-support workload",
        },
        "search_runbook": {
            "runbook": "Runtime timeout response",
            "steps": [
                "Confirm dependency health and recent deploys.",
                "Reduce concurrency only if error rate exceeds 5%.",
                "Escalate after 30 minutes or a customer-impacting SLA breach.",
            ],
            "source": "Operations handbook v3.2",
        },
        "get_access_review": {
            "overdue_reviews": 2,
            "roles": ["ProductionAdmin", "GatewayIntegrationMaintainer"],
            "action": "Create an approval-backed access review ticket.",
        },
    }
    output = responses[name]
    duration_ms = max(1, round((time.perf_counter() - started) * 1000))
    return ToolCall(
        name=name,
        input=payload,
        output=output,
        duration_ms=duration_ms,
        policy_decision="allow",
    )
