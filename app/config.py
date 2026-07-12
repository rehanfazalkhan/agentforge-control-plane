"""Runtime configuration with explicit production safety gates."""

from __future__ import annotations

import os
from dataclasses import dataclass


class ConfigurationError(RuntimeError):
    """Raised when a production runtime is missing a mandatory control."""


@dataclass(frozen=True)
class Settings:
    runtime_mode: str = "development"
    aws_region: str = "us-east-1"
    bedrock_model_id: str | None = None
    bedrock_max_tokens: int = 1200
    bedrock_temperature: float = 0.2
    run_store: str = "memory"
    dynamodb_table: str | None = None
    jwt_issuer: str | None = None
    jwt_audience: str | None = None
    jwt_role_claim: str = "custom:role"
    tool_timeout_seconds: float = 8.0
    service_health_url: str | None = None
    cost_forecast_url: str | None = None
    runbook_search_url: str | None = None
    access_review_url: str | None = None

    @property
    def is_production(self) -> bool:
        return self.runtime_mode == "production"

    @classmethod
    def from_environment(cls) -> "Settings":
        return cls(
            runtime_mode=os.getenv("AGENTFORGE_RUNTIME_MODE", "development").lower(),
            aws_region=os.getenv("AWS_REGION", "us-east-1"),
            bedrock_model_id=os.getenv("BEDROCK_MODEL_ID"),
            bedrock_max_tokens=int(os.getenv("BEDROCK_MAX_TOKENS", "1200")),
            bedrock_temperature=float(os.getenv("BEDROCK_TEMPERATURE", "0.2")),
            run_store=os.getenv("AGENTFORGE_RUN_STORE", "memory").lower(),
            dynamodb_table=os.getenv("AGENTFORGE_RUN_TABLE"),
            jwt_issuer=os.getenv("AGENTFORGE_JWT_ISSUER"),
            jwt_audience=os.getenv("AGENTFORGE_JWT_AUDIENCE"),
            jwt_role_claim=os.getenv("AGENTFORGE_JWT_ROLE_CLAIM", "custom:role"),
            tool_timeout_seconds=float(os.getenv("AGENTFORGE_TOOL_TIMEOUT_SECONDS", "8")),
            service_health_url=os.getenv("AGENTFORGE_TOOL_SERVICE_HEALTH_URL"),
            cost_forecast_url=os.getenv("AGENTFORGE_TOOL_COST_FORECAST_URL"),
            runbook_search_url=os.getenv("AGENTFORGE_TOOL_RUNBOOK_SEARCH_URL"),
            access_review_url=os.getenv("AGENTFORGE_TOOL_ACCESS_REVIEW_URL"),
        )

    def tool_endpoint(self, tool_name: str) -> str | None:
        return {
            "get_service_health": self.service_health_url,
            "get_cost_forecast": self.cost_forecast_url,
            "search_runbook": self.runbook_search_url,
            "get_access_review": self.access_review_url,
        }.get(tool_name)

    def production_gaps(self) -> list[str]:
        if not self.is_production:
            return []
        required = {
            "BEDROCK_MODEL_ID": self.bedrock_model_id,
            "AGENTFORGE_RUN_STORE=dynamodb": self.run_store == "dynamodb",
            "AGENTFORGE_RUN_TABLE": self.dynamodb_table,
            "AGENTFORGE_JWT_ISSUER": self.jwt_issuer,
            "AGENTFORGE_JWT_AUDIENCE": self.jwt_audience,
            "AGENTFORGE_TOOL_SERVICE_HEALTH_URL": self.service_health_url,
            "AGENTFORGE_TOOL_COST_FORECAST_URL": self.cost_forecast_url,
            "AGENTFORGE_TOOL_RUNBOOK_SEARCH_URL": self.runbook_search_url,
            "AGENTFORGE_TOOL_ACCESS_REVIEW_URL": self.access_review_url,
        }
        return [name for name, value in required.items() if not value]

    def assert_ready_for_production(self) -> None:
        if self.runtime_mode not in {"development", "production"}:
            raise ConfigurationError("AGENTFORGE_RUNTIME_MODE must be development or production.")
        gaps = self.production_gaps()
        if gaps:
            raise ConfigurationError(
                "Production runtime is not configured. Missing: " + ", ".join(gaps)
            )
