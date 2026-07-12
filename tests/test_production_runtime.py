from __future__ import annotations

from app.auth import Principal
from app.config import ConfigurationError, Settings
from app.model_runtime import BedrockConverseEngine
from app.models import ToolCall


class FakeBedrockClient:
    def __init__(self) -> None:
        self.requests: list[dict] = []
        self.responses = [
            {
                "output": {"message": {"content": [{"toolUse": {"toolUseId": "tool-1", "name": "search_runbook", "input": {"query": "timeout"}}}]}},
                "usage": {"inputTokens": 10, "outputTokens": 5, "totalTokens": 15},
            },
            {
                "output": {"message": {"content": [{"text": "The approved runbook recommends confirming dependency health. Recommend escalation if the SLA is breached."}]}},
                "usage": {"inputTokens": 20, "outputTokens": 12, "totalTokens": 32},
            },
        ]

    def converse(self, **request):
        self.requests.append(request)
        return self.responses.pop(0)


class FakeToolExecutor:
    def invoke(self, principal: Principal, name: str, payload: dict) -> ToolCall:
        assert principal.role == "operator"
        assert name == "search_runbook"
        return ToolCall(name=name, input=payload, output={"source": "Operations handbook v3.2"}, duration_ms=2, policy_decision="allow")


def production_settings() -> Settings:
    return Settings(
        runtime_mode="production",
        aws_region="us-east-1",
        bedrock_model_id="amazon.nova-lite-v1:0",
        run_store="dynamodb",
        dynamodb_table="agentforge-runs-production",
        jwt_issuer="https://issuer.example.com",
        jwt_audience="agentforge-api",
        service_health_url="https://gateway.example.com/service-health",
        cost_forecast_url="https://gateway.example.com/cost-forecast",
        runbook_search_url="https://gateway.example.com/runbook-search",
        access_review_url="https://gateway.example.com/access-review",
    )


def test_production_settings_fail_closed_when_required_controls_are_missing() -> None:
    settings = Settings(runtime_mode="production")

    assert "BEDROCK_MODEL_ID" in settings.production_gaps()
    try:
        settings.assert_ready_for_production()
    except ConfigurationError as error:
        assert "AGENTFORGE_JWT_ISSUER" in str(error)
    else:  # pragma: no cover
        raise AssertionError("production settings must fail closed")


def test_bedrock_engine_executes_bounded_tool_loop_and_accounts_tokens() -> None:
    client = FakeBedrockClient()
    settings = production_settings()

    result = BedrockConverseEngine(settings, client=client).execute(
        "Investigate the timeout incident", Principal("user-123", "operator"), FakeToolExecutor()
    )

    assert result.route == "bedrock-supervisor"
    assert result.model_id == "amazon.nova-lite-v1:0"
    assert result.token_usage == {"input_tokens": 30, "output_tokens": 17, "total_tokens": 47}
    assert result.tool_calls[0].name == "search_runbook"
    assert len(client.requests) == 2
    assert client.requests[0]["toolConfig"]["tools"]
