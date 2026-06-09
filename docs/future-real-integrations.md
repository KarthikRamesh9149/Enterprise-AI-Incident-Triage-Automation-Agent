# Future Real Integrations

Mock Slack can become real Slack by replacing the notification executor with Slack API calls after adding scoped tokens, channel allowlists, payload review, retry controls, and audit-preserving response storage.

Mock Jira/GitHub ticket creation can become real integration by replacing ticket executors with Jira or GitHub APIs after adding project/repository allowlists, field validation, duplicate detection, and approval gates.

Logs can connect to Datadog, CloudWatch, Grafana, or OpenSearch by implementing read-only MCP tools with query allowlists, result limits, redaction, and latency budgets.

PagerDuty/Opsgenie can be added as approval-gated escalation tools with explicit escalation policies and dry-run previews.

Before enabling real actions:

- Harden secrets management.
- Add per-tool egress policy.
- Add stronger rate limiting.
- Add tenant and environment isolation.
- Keep approval and audit gates mandatory.
- Run evals for unsafe action prevention.

