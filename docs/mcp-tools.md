# MCP-Style Tools

This repository implements an MCP-style internal tool registry: named tools, typed schemas, risk levels, permission levels, enable/disable governance, approval requirements, timeout/rate-limit fields, structured outputs, tool-call persistence, and audit logs.

The implementation is intentionally local and mock-backed. It can be adapted later to official MCP servers or internal enterprise tools by replacing handlers in `backend/app/mcp/tools.py`.

Risk levels:

- Low: read-only local context.
- Medium: drafts or communication artifacts.
- High: future real external side effects.

Permission levels:

- Viewer can read safe incident details.
- Engineer can run read-only tools.
- Incident commander can create drafts and approve incident actions.
- Admin can govern tools and inspect audit data.

