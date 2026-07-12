# AgentCore deployment path

AgentForge is a production-grade codebase with a real Bedrock runtime path. This document describes the account-specific deployment to Amazon Bedrock AgentCore. It does **not** claim that AWS resources have been created until the deployment commands are actually run.

## What maps to AgentCore

| AgentForge capability | AgentCore service / AWS control |
| --- | --- |
| Supervisor and domain specialists | AgentCore Runtime, using the `/invocations` and `/ping` routes already exposed by `app.main` |
| Allow-listed tool catalog | AgentCore Gateway, with Lambda, OpenAPI, or MCP server targets |
| `actor_role` authorization | AgentCore Identity plus JWT/OIDC claims; replace the local role field with verified identity claims |
| DynamoDB run ledger | AgentCore Memory for user-scoped conversation state when retention and consent are approved |
| Structured trace objects | AgentCore Observability and CloudWatch, using OpenTelemetry instrumentation |
| Release gates | AgentCore Evaluations: built-in evaluators plus a code-based custom evaluator |

## Preflight

1. Use an AWS account and approved Region with an owner for billing, model access, data retention, and incident response.
2. Configure an AWS profile with least-privilege deployment permissions and enable the desired Bedrock model.
3. Install Node.js 20 or later and the AgentCore CLI: `npm install -g @aws/agentcore`.
4. Install the Python SDK when adding managed resources: `pip install bedrock-agentcore`.
5. Set `AWS_REGION` and `AGENTFORGE_ENVIRONMENT`; do not put credentials in `.env` or source control.

## Deploy safely

Start from a separate branch after account access has been approved:

```bash
agentcore create --name agentforge-runtime
cd agentforge-runtime
# Bring in this project's app/ package and its container configuration.
agentcore dev --no-browser
agentcore deploy --plan
agentcore deploy
agentcore status
```

The CLI creates the `agentcore/agentcore.json` and `agentcore/aws-targets.json` files for the selected account and Region. Keep those account-bound values out of this public repository unless they have been reviewed.

## Production hardening checklist

- Replace `actor_role` request input with authenticated claims from an OIDC provider.
- Put each external integration behind Gateway targets; define per-tool scopes and resource policies.
- Enable Gateway MCP sessions only with inbound authentication; use the shortest feasible timeout.
- Add OpenTelemetry instrumentation, redact sensitive request fields, and enable CloudWatch transaction search.
- Move the release gates to AgentCore Evaluations and include a golden dataset before promoting a release.
- Configure budgets, anomaly detection, CloudWatch alarms, retention, and a cleanup runbook before accepting production traffic.

## Suggested rollout

1. Deploy only `search_runbook` using synthetic data.
2. Add one low-risk read-only integration through Gateway.
3. Run a golden evaluation dataset and confirm trace redaction.
4. Add real identity, then enable the remaining tools one by one.

See the current [AWS AgentCore CLI guide](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-get-started-cli.html), [Gateway documentation](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/gateway-using.html), and [Observability guide](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/observability.html) before deployment.
