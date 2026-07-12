"""Central policy enforcement for tool execution and input safety."""

from __future__ import annotations

import re


class PolicyViolation(ValueError):
    """Raised when an operation violates a non-bypassable control."""


INJECTION_PATTERNS = (
    r"ignore (all |any |the )?(previous|prior) instructions",
    r"reveal (the )?(system|developer) prompt",
    r"you are now",
    r"bypass (the )?(guardrail|policy|security)",
)

TOOL_ROLES: dict[str, set[str]] = {
    "get_service_health": {"operator", "analyst", "admin"},
    "get_cost_forecast": {"analyst", "admin"},
    "search_runbook": {"operator", "analyst", "admin"},
    "get_access_review": {"admin"},
}


def validate_input(text: str) -> None:
    normalized = text.lower()
    if any(re.search(pattern, normalized) for pattern in INJECTION_PATTERNS):
        raise PolicyViolation(
            "This request was blocked by the prompt-injection safety policy. "
            "Try asking the operational question directly."
        )


def authorize_tool(actor_role: str, tool_name: str) -> None:
    allowed_roles = TOOL_ROLES.get(tool_name)
    if allowed_roles is None:
        raise PolicyViolation(f"Tool '{tool_name}' is not registered in the gateway.")
    if actor_role not in allowed_roles:
        raise PolicyViolation(
            f"The '{actor_role}' role is not allowed to invoke '{tool_name}'."
        )
