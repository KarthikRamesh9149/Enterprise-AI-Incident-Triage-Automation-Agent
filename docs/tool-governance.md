# Tool Governance

Admins can inspect and patch tool governance settings:

- `is_enabled`
- `risk_level`
- `requires_approval`
- `permission_level`
- `rate_limit_per_minute`
- `timeout_ms`

Every tool call stores input, output, status, latency, caller, incident ID, and audit metadata. High-risk future tools should require approvals and explicit operator review before execution.

