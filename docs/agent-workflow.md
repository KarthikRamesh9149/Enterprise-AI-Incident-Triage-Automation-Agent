# Agent Workflow

State includes incident ID, service context, logs, runbooks, health, recent changes, related incidents, hypotheses, remediation plan, drafts, risk findings, approval IDs, and trace IDs.

Nodes:

- Alert intake loads or creates incident context.
- Severity classifier uses deterministic rules.
- Context planner selects expected tools.
- Tool permission planner blocks restricted tools based on role.
- Log search retrieves redacted logs.
- Service health checks deterministic mock health.
- Runbook search flags prompt injection.
- Recent changes and related incidents provide causal evidence.
- Root cause analyzer creates scored hypotheses.
- Remediation planner creates approval-gated steps.
- Ticket/status draft nodes create pending approvals when role policy allows.
- Risk checker marks external actions as mock-only and approval-gated.
- Timeline writer persists agent events.
- Final summary uses mock synthesis by default or optional OpenAI Responses API when configured.

The workflow stores each node in `agent_trace_steps` for the trace viewer.

