"""Development engine and shared result model for agent execution."""

from __future__ import annotations

from dataclasses import dataclass, field

from .auth import Principal
from .models import ToolCall
from .tools import ToolExecutor


@dataclass
class AgentResult:
    route: str
    response: str
    citations: list[str]
    tool_calls: list[ToolCall]
    model_id: str | None = None
    token_usage: dict[str, int] = field(default_factory=dict)


def choose_route(question: str) -> str:
    query = question.lower()
    if any(term in query for term in ("cost", "spend", "budget", "forecast")):
        return "finops"
    if any(term in query for term in ("access", "permission", "role", "security")):
        return "security"
    if any(term in query for term in ("incident", "outage", "error", "latency", "health")):
        return "incident"
    return "operations"


def execute_development_specialist(question: str, principal: Principal, tools: ToolExecutor) -> AgentResult:
    """Deterministic local engine used only for development and contract tests."""
    route = choose_route(question)
    if route == "finops":
        call = tools.invoke(principal, "get_cost_forecast", {})
        data = call.output
        variance = data["forecast_usd"] - data["budget_usd"]
        return AgentResult(
            route, f"Forecasted monthly spend is ${data['forecast_usd']:,}, ${variance:,} above budget. "
            f"The leading driver is {data['largest_driver']}. Recommend reviewing model routing and setting a daily spend alert before changing production limits.",
            ["FinOps ledger fixture"], [call], model_id="development-engine",
        )
    if route == "security":
        call = tools.invoke(principal, "get_access_review", {})
        data = call.output
        return AgentResult(
            route, f"{data['overdue_reviews']} privileged reviews are overdue: {', '.join(data['roles'])}. "
            f"{data['action']} Recommend assigning the review to the designated application owner today.",
            ["Identity governance fixture"], [call], model_id="development-engine",
        )
    if route == "incident":
        health = tools.invoke(principal, "get_service_health", {"service": "agent-runtime"})
        runbook = tools.invoke(principal, "search_runbook", {"query": "runtime timeout"})
        data = health.output
        return AgentResult(
            route, f"The agent runtime is {data['status']} with {data['error_rate']} errors and p95 latency of {data['p95_latency_ms']} ms. "
            f"{data['signal']} Recommend confirming dependency health and recent deploys; do not reduce concurrency unless the error rate exceeds 5%.",
            [str(runbook.output["source"])], [health, runbook], model_id="development-engine",
        )
    call = tools.invoke(principal, "search_runbook", {"query": question})
    return AgentResult(
        route, "The approved runbook is 'Runtime timeout response'. Start by confirming dependency health and recent deploys, then escalate after 30 minutes or a customer-impacting SLA breach. Recommend documenting the decision in the incident record.",
        [str(call.output["source"])], [call], model_id="development-engine",
    )
