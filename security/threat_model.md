# Repository Threat Model

## Assets and Privileges

- User accounts, password hashes, JWTs, and role assignments.
- Incident records, alerts, logs, runbooks, tool calls, reports, audit logs, and security events.
- Tool governance settings that control what actions can run.
- Approval records that gate mock external actions.
- Optional OpenAI API key stored outside the repo in local environment variables.

## Trust Boundaries

- Browser to FastAPI API over local HTTP.
- Authenticated user context to RBAC-protected backend routes.
- MCP-style tool registry to individual tool handlers.
- Agent workflow to tool execution and approval creation.
- Local database to report export filesystem.
- Optional OpenAI provider boundary when `LLM_PROVIDER=openai`.

## Attacker-Controlled Inputs

- Registration/login fields.
- Incident, alert, runbook, and tool payload request bodies.
- Runbook content that may contain prompt-injection attempts.
- Application log messages that may contain secrets or hostile text.
- Approval notes and report-generation requests.

## Required Invariants

- Passwords are never stored or returned in plaintext.
- JWTs and API keys are not logged or exposed.
- Viewer role cannot run tools or approve actions.
- Engineer role cannot approve restricted actions.
- External-facing actions remain mock-only and approval-gated.
- Tool calls are allowlisted, permission-checked, persisted, and audited.
- Logs and reports expose redacted evidence.
- Prompt-injection warnings are persisted and visible.

## Repository-Wide Failure Modes

- RBAC bypass allowing tool execution or admin access.
- Approval bypass causing mock actions to execute without review.
- Secret leakage through logs, reports, tool outputs, traces, or audit events.
- Prompt-injection content influencing agent/tool policy.
- Tool governance changes not audited.
- Optional OpenAI failures breaking the local deterministic demo.

