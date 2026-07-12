"""Supervisor routing and specialized agents for the control-plane demo."""

from __future__ import annotations

from dataclasses import dataclass

from .models import ToolCall
from .tools import invoke_tool


@dataclass
class AgentResult:
    route: str
    response: str
    citations: list[str]
    tool_calls: list[ToolCall]


def choose_route(question: str) -> str:
    query = question.lower()
    if any(term in query for term in ("cost", "spend", "budget", "forecast")):
        return "finops"
    if any(term in query for term in ("access", "permission", "role", "security")):
        return "security"
    if any(term in query for term in ("incident", "outage", "error", "latency", "health")):
        return "incident"
    return "operations"


def execute_specialist(question: str, actor_role: str) -> AgentResult:
    """Route to one bounded specialist; tools remain policy-governed."""
    route = choose_route(question)
    if route == "finops":
        call = invoke_tool(actor_role, "get_cost_forecast", {})
        data = call.output
        variance = data["forecast_usd"] - data["budget_usd"]
        response = (
            f"Forecasted monthly spend is ${data['forecast_usd']:,}, which is "
            f"${variance:,} above the ${data['budget_usd']:,} budget. The main driver is "
            f"{data['largest_driver']}. Recommend reviewing model routing and setting a "
            "daily spend alert before changing production limits."
        )
        return AgentResult(route, response, ["FinOps ledger: July demo snapshot"], [call])

    if route == "security":
        call = invoke_tool(actor_role, "get_access_review", {})
        data = call.output
        response = (
            f"{data['overdue_reviews']} privileged access reviews are overdue: "
            f"{', '.join(data['roles'])}. {data['action']} No access changes were made."
            " Recommend assigning the review to the designated application owner today."
        )
        return AgentResult(route, response, ["Identity governance register"], [call])

    if route == "incident":
        health = invoke_tool(actor_role, "get_service_health", {"service": "agent-runtime"})
        runbook = invoke_tool(actor_role, "search_runbook", {"query": "runtime timeout"})
        data = health.output
        response = (
            f"The agent runtime is {data['status']} with {data['error_rate']} errors and "
            f"p95 latency of {data['p95_latency_ms']} ms. {data['signal']} "
            "Recommended next step: confirm dependency health and recent deploys; do not "
            "reduce concurrency unless the error rate exceeds 5%."
        )
        return AgentResult(route, response, [runbook.output["source"]], [health, runbook])

    call = invoke_tool(actor_role, "search_runbook", {"query": question})
    response = (
        "I routed this to Operations. The approved runbook is 'Runtime timeout response'. "
        "Start by confirming dependency health and recent deploys, then escalate after "
        "30 minutes or a customer-impacting SLA breach."
    )
    return AgentResult(route, response, [call.output["source"]], [call])
