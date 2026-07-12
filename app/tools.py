"""Governed tool contracts and production HTTPS dispatch for AgentForge."""

from __future__ import annotations

import json
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .auth import Principal
from .config import Settings
from .models import ToolCall
from .policy import authorize_tool


TOOL_CATALOG: list[dict[str, Any]] = [
    {
        "name": "get_service_health",
        "description": "Read current service health, error rate, and latency for an allow-listed service.",
        "roles": ["operator", "analyst", "admin"],
        "input_schema": {
            "type": "object",
            "properties": {"service": {"type": "string", "description": "Approved service identifier."}},
            "required": ["service"],
        },
    },
    {
        "name": "get_cost_forecast",
        "description": "Read current cloud spend, forecast, budget, and primary cost driver.",
        "roles": ["analyst", "admin"],
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "search_runbook",
        "description": "Search approved operational runbooks and return cited, read-only guidance.",
        "roles": ["operator", "analyst", "admin"],
        "input_schema": {
            "type": "object",
            "properties": {"query": {"type": "string", "maxLength": 500}},
            "required": ["query"],
        },
    },
    {
        "name": "get_access_review",
        "description": "Read privileged roles that are due for an approval-backed access review.",
        "roles": ["admin"],
        "input_schema": {"type": "object", "properties": {}},
    },
]


def bedrock_tool_configuration() -> dict[str, Any]:
    """Return the Bedrock Converse tool schema used by the production agent loop."""
    return {
        "tools": [
            {
                "toolSpec": {
                    "name": tool["name"],
                    "description": tool["description"],
                    "inputSchema": {"json": tool["input_schema"]},
                }
            }
            for tool in TOOL_CATALOG
        ]
    }


class ToolExecutor:
    """Policy-first execution boundary for Gateway or HTTPS tool targets."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def invoke(self, principal: Principal, name: str, payload: dict[str, Any]) -> ToolCall:
        started = time.perf_counter()
        authorize_tool(principal.role, name)
        output = self._invoke_production(principal, name, payload) if self.settings.is_production else self._development_response(name, payload)
        return ToolCall(
            name=name,
            input=payload,
            output=output,
            duration_ms=max(1, round((time.perf_counter() - started) * 1000)),
            policy_decision="allow",
        )

    def denied_call(self, name: str, payload: dict[str, Any], reason: str) -> ToolCall:
        return ToolCall(
            name=name,
            input=payload,
            output={"error": "Tool access denied by policy."},
            duration_ms=0,
            policy_decision="deny",
        )

    def _invoke_production(self, principal: Principal, name: str, payload: dict[str, Any]) -> dict[str, Any]:
        endpoint = self.settings.tool_endpoint(name)
        if not endpoint or not endpoint.startswith("https://"):
            raise RuntimeError(f"Production endpoint for '{name}' must be configured with HTTPS.")
        request_body = json.dumps({"input": payload}).encode("utf-8")
        request = Request(
            endpoint,
            data=request_body,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "X-AgentForge-Subject": principal.subject,
                "X-AgentForge-Role": principal.role,
            },
        )
        try:
            with urlopen(request, timeout=self.settings.tool_timeout_seconds) as response:  # nosec B310 - HTTPS is enforced above
                body = response.read().decode("utf-8")
                parsed = json.loads(body)
                if not isinstance(parsed, dict):
                    raise RuntimeError(f"Tool '{name}' returned a non-object response.")
                return parsed
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as error:
            raise RuntimeError(f"Tool '{name}' is unavailable; no action was performed.") from error

    @staticmethod
    def _development_response(name: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Fixtures support local development and contract tests only, never production mode."""
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
                "largest_driver": "Foundation-model inference on the support workload",
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
        return responses[name]
