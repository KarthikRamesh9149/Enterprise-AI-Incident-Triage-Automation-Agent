# Security

Auth uses email/password login, password hashing, JWT tokens, and reusable role dependencies. Roles are `admin`, `incident_commander`, `engineer`, and `viewer`.

Tool security controls:

- Tool allowlist.
- Enable/disable governance.
- Role checks before execution.
- Approval gates for mock external actions.
- Audit logs for calls and administrative actions.
- Security events for denied tool access and prompt-injection findings.

Sensitive data redaction detects API keys, tokens, bearer tokens, passwords, and email addresses. Reports and log search return redacted content.

Runbook prompt-injection detection flags content attempting to ignore instructions, reveal hidden prompts, bypass approval, exfiltrate data, or disable security/audit controls.

No real secrets should be committed. `.env.example` contains local defaults only.

