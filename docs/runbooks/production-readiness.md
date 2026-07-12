# Production readiness gate

AgentForge intentionally fails closed in `AGENTFORGE_RUNTIME_MODE=production`. A deployment is not ready unless all of the following are true:

1. A permitted Bedrock model is configured in `BEDROCK_MODEL_ID` and the runtime role can invoke it.
2. DynamoDB is provisioned through `infra/terraform`, and `AGENTFORGE_RUN_STORE=dynamodb` plus `AGENTFORGE_RUN_TABLE` are set.
3. A real JWT issuer and audience are configured. The API derives roles from verified claims; it never trusts `actor_role` from a production request body.
4. Every tool endpoint is HTTPS and fronts an approved read-only service or AgentCore Gateway target.
5. The AgentCore Runtime execution role is least privilege, scoped with `aws:SourceAccount` and `aws:SourceArn`, and runs a non-root container.
6. CloudWatch retention, a budget alarm, on-call routing, and data retention policy have an approved owner.

Run `/readyz` before traffic is enabled. It returns `503` with the missing configuration keys if the service is not safe to accept production requests.

## Incident response

- **Model or tool errors:** inspect the run ID and CloudWatch structured event. Do not replay a write-capable operation automatically.
- **Authorization failure:** validate the JWT issuer, audience, `sub`, and configured role claim. Do not assign roles from request data.
- **Evaluation regression:** freeze deployment promotion, select affected traces, run AgentCore on-demand evaluation, and compare with the golden dataset.
- **Suspected prompt injection:** preserve trace metadata, block the request, and update the injection test corpus before release.
