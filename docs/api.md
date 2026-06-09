# API

All protected endpoints require `Authorization: Bearer <jwt>`.

Health:

- `GET /health`

Authentication:

- `POST /auth/register`
- `POST /auth/login`
- `GET /auth/me`

Services:

- `GET /services`
- `GET /services/{service_id}`

Incidents:

- `POST /incidents` engineer+
- `GET /incidents`
- `GET /incidents/{incident_id}`
- `PATCH /incidents/{incident_id}` incident commander+
- `GET /incidents/{incident_id}/timeline`
- `GET /incidents/{incident_id}/logs`
- `GET /incidents/{incident_id}/runbooks`
- `GET /incidents/{incident_id}/tool-calls`
- `GET /incidents/{incident_id}/approvals`
- `GET /incidents/{incident_id}/agent-runs`
- `GET /incidents/{incident_id}/reports`

Alerts:

- `POST /alerts` engineer+
- `GET /alerts`
- `GET /alerts/{alert_id}`

Runbooks:

- `POST /runbooks` engineer+
- `GET /runbooks`
- `GET /runbooks/{runbook_id}`
- `PATCH /runbooks/{runbook_id}` engineer+
- `GET /runbooks/{runbook_id}/security-check`

MCP-style tools:

- `GET /mcp/tools`
- `GET /mcp/tools/{tool_name}`
- `POST /mcp/tools/search-logs`
- `POST /mcp/tools/search-runbooks`
- `POST /mcp/tools/get-incident-details`
- `POST /mcp/tools/get-service-health`
- `POST /mcp/tools/create-ticket-draft`
- `POST /mcp/tools/draft-status-update`
- `POST /mcp/tools/list-recent-service-changes`
- `POST /mcp/tools/get-related-incidents`

Agent:

- `POST /agent/run-incident-triage` engineer+
- `GET /agent/runs`
- `GET /agent/runs/{agent_run_id}`
- `GET /agent/runs/{agent_run_id}/trace`
- `GET /agent/runs/{agent_run_id}/summary`

Approvals:

- `GET /approvals`
- `GET /approvals/{approval_id}`
- `POST /approvals/{approval_id}/approve` incident commander+
- `POST /approvals/{approval_id}/reject` incident commander+
- `POST /approvals/{approval_id}/request-revision` incident commander+

Mock actions:

- `POST /actions/mock-create-ticket` incident commander+
- `POST /actions/mock-send-status-update` incident commander+
- `POST /actions/mock-escalate-incident` incident commander+
- `POST /actions/mock-resolve-incident` incident commander+

Reports:

- `POST /reports/generate` engineer+
- `GET /reports`
- `GET /reports/{report_id}`
- `GET /reports/{report_id}/download`

Evaluations:

- `POST /evals/run` admin
- `GET /evals/runs`
- `GET /evals/runs/{run_id}`
- `GET /evals/runs/{run_id}/cases`
- `GET /evals/summary`

Admin:

- `GET /admin/audit-logs`
- `GET /admin/tool-calls`
- `GET /admin/analytics`
- `GET /admin/observability`
- `GET /admin/tool-governance`
- `PATCH /admin/tool-governance/{tool_id}`
- `GET /admin/security`
- `GET /admin/users`
- `GET /admin/system-health`

