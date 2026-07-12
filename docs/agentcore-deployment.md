# AgentCore deployment path

AgentForge is fully runnable locally. This document describes the intentional, account-specific handoff to Amazon Bedrock AgentCore. It does **not** claim that AWS resources have been created.

## What maps to AgentCore

| AgentForge capability | AgentCore service / AWS control |
| --- | --- |
| Supervisor and domain specialists | AgentCore Runtime, using the `/invocations` and `/ping` routes already exposed by `app.main` |
| Allow-listed tool catalog | AgentCore Gateway, with Lambda, OpenAPI, or MCP server targets |
| `actor_role` authorization | AgentCore Identity plus JWT/OIDC claims; replace the local role field with verified identity claims |
| In-memory session history | AgentCore Memory, scoped per end user and session |
| Local trace objects | AgentCore Observability and CloudWatch, using OpenTelemetry instrumentation |
| Deterministic evaluation gates | AgentCore Evaluations: built-in evaluators plus a code-based custom evaluator |

## Preflight

1. Use an AWS account dedicated to this demo and select a supported Region.
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
- Move the deterministic release gates to AgentCore Evaluations and include a golden dataset before promoting a release.
- Configure budgets, anomaly detection, CloudWatch alarms, retention, and a cleanup runbook before public demos.

## Suggested rollout

1. Deploy only `search_runbook` using synthetic data.
2. Add one low-risk read-only integration through Gateway.
3. Run a golden evaluation dataset and confirm trace redaction.
4. Add real identity, then enable the remaining tools one by one.

See the current [AWS AgentCore CLI guide](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-get-started-cli.html), [Gateway documentation](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/gateway-using.html), and [Observability guide](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/observability.html) before deployment.
