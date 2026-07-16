import time
from collections.abc import Callable
from typing import Any

from fastapi import HTTPException
from sqlalchemy import desc, or_, select
from sqlalchemy.orm import Session

from app.core.auth import role_allows
from app.db import models
from app.security.redaction import detect_prompt_injection, redact_sensitive_text
from app.services.audit import audit, security_event, timeline

ToolFunc = Callable[[Session, models.User, dict[str, Any]], dict[str, Any]]


def _incident(db: Session, incident_id: str) -> models.Incident:
    incident = db.get(models.Incident, incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    return incident


def search_logs(db: Session, user: models.User, payload: dict[str, Any]) -> dict[str, Any]:
    incident_id = payload.get("incident_id")
    query = str(payload.get("query", "")).lower()
    limit = min(int(payload.get("limit", 20)), 100)
    statement = select(models.ApplicationLog)
    if incident_id:
        statement = statement.where(models.ApplicationLog.incident_id == incident_id)
    if query:
        statement = statement.where(models.ApplicationLog.message.ilike(f"%{query}%"))
    logs = db.scalars(statement.order_by(desc(models.ApplicationLog.timestamp)).limit(limit)).all()
    rows = []
    total_redactions = 0
    for log in logs:
        redacted, count = redact_sensitive_text(log.message)
        if redacted != log.redacted_message or count != log.redaction_count:
            log.redacted_message = redacted
            log.redaction_count = count
        total_redactions += count
        rows.append(
            {
                "id": log.id,
                "timestamp": log.timestamp.isoformat(),
                "level": log.level,
                "message": redacted,
                "trace_id": log.trace_id,
                "redaction_count": count,
            }
        )
    return {"logs": rows, "count": len(rows), "redaction_count": total_redactions}


def search_runbooks(db: Session, user: models.User, payload: dict[str, Any]) -> dict[str, Any]:
    query = str(payload.get("query", "")).lower()
    service_id = payload.get("service_id")
    statement = select(models.Runbook)
    if service_id:
        statement = statement.where(models.Runbook.service_id == service_id)
    if query:
        statement = statement.where(
            or_(
                models.Runbook.title.ilike(f"%{query}%"), models.Runbook.content.ilike(f"%{query}%")
            )
        )
    rows = []
    for runbook in db.scalars(statement.limit(50)).all():
        findings = detect_prompt_injection(runbook.content)
        runbook.injection_warning = bool(findings)
        runbook.injection_findings_json = findings
        rows.append(
            {
                "id": runbook.id,
                "title": runbook.title,
                "summary": runbook.summary,
                "trust_score": runbook.trust_score,
                "injection_warning": runbook.injection_warning,
                "injection_findings": findings,
            }
        )
        if findings:
            security_event(
                db,
                user_id=user.id,
                event_type="runbook_prompt_injection_detected",
                severity="high",
                resource_type="runbook",
                resource_id=runbook.id,
                details={"findings": findings},
            )
    return {"runbooks": rows, "count": len(rows)}


def get_incident_details(db: Session, user: models.User, payload: dict[str, Any]) -> dict[str, Any]:
    incident = _incident(db, payload["incident_id"])
    service = db.get(models.Service, incident.service_id)
    return {
        "incident": serialize(incident),
        "service": serialize(service) if service else None,
    }


def get_service_health(db: Session, user: models.User, payload: dict[str, Any]) -> dict[str, Any]:
    service_id = payload.get("service_id")
    incident_id = payload.get("incident_id")
    if incident_id and not service_id:
        service_id = _incident(db, incident_id).service_id
    service = db.get(models.Service, service_id)
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    status = "degraded" if service.name == "checkout-api" else "healthy"
    return {
        "service_id": service.id,
        "service_name": service.name,
        "status": status,
        "checks": [
            {
                "name": "http-p95-latency",
                "status": "failing" if status == "degraded" else "passing",
            },
            {"name": "database-connectivity", "status": "passing"},
            {
                "name": "dependency-payments-gateway",
                "status": "failing" if status == "degraded" else "passing",
            },
        ],
    }


def list_recent_service_changes(
    db: Session, user: models.User, payload: dict[str, Any]
) -> dict[str, Any]:
    incident_id = payload.get("incident_id")
    service_id = payload.get("service_id") or (
        _incident(db, incident_id).service_id if incident_id else None
    )
    changes = db.scalars(
        select(models.ServiceChange)
        .where(models.ServiceChange.service_id == service_id)
        .order_by(desc(models.ServiceChange.changed_at))
        .limit(20)
    ).all()
    return {"changes": [serialize(change) for change in changes], "count": len(changes)}


def get_related_incidents(
    db: Session, user: models.User, payload: dict[str, Any]
) -> dict[str, Any]:
    incident_id = payload["incident_id"]
    related = db.scalars(
        select(models.RelatedIncident).where(
            models.RelatedIncident.source_incident_id == incident_id
        )
    ).all()
    return {"related_incidents": [serialize(row) for row in related], "count": len(related)}


def create_ticket_draft(db: Session, user: models.User, payload: dict[str, Any]) -> dict[str, Any]:
    incident = _incident(db, payload["incident_id"])
    ticket = models.Ticket(
        incident_id=incident.id,
        title=f"[{incident.severity.upper()}] {incident.title}",
        body=payload.get(
            "body",
            (
                f"Mock ticket draft for {incident.title}. Impact: checkout timeout spike. "
                "Suggested rollback requires approval."
            ),
        ),
        created_by=user.id,
    )
    db.add(ticket)
    db.flush()
    approval = models.Approval(
        incident_id=incident.id,
        requested_by=user.id,
        action_type="mock_create_ticket",
        resource_type="ticket",
        resource_id=ticket.id,
        status="pending",
        request_reason=(
            "External ticket creation is represented as a mock action and requires "
            "commander/admin approval."
        ),
    )
    db.add(approval)
    db.flush()
    timeline(
        db,
        incident_id=incident.id,
        event_type="approval.requested",
        title="Ticket draft awaiting approval",
        description=ticket.title,
        actor_type="user",
        actor_id=user.id,
        metadata={"approval_id": approval.id},
    )
    return {"ticket": serialize(ticket), "approval": serialize(approval)}


def draft_status_update(db: Session, user: models.User, payload: dict[str, Any]) -> dict[str, Any]:
    incident = _incident(db, payload["incident_id"])
    notification = models.Notification(
        incident_id=incident.id,
        channel="mock-slack-status",
        audience=payload.get("audience", "internal-incident-channel"),
        draft_text=payload.get(
            "draft_text",
            (
                f"Investigating {incident.title}. Current severity {incident.severity}. "
                "Next update in 15 minutes."
            ),
        ),
        created_by=user.id,
    )
    db.add(notification)
    db.flush()
    approval = models.Approval(
        incident_id=incident.id,
        requested_by=user.id,
        action_type="mock_send_status_update",
        resource_type="notification",
        resource_id=notification.id,
        status="pending",
        request_reason="Status updates are mock external communications and require approval.",
    )
    db.add(approval)
    db.flush()
    timeline(
        db,
        incident_id=incident.id,
        event_type="approval.requested",
        title="Status update awaiting approval",
        description=notification.draft_text,
        actor_type="user",
        actor_id=user.id,
        metadata={"approval_id": approval.id},
    )
    return {"notification": serialize(notification), "approval": serialize(approval)}


def request_incident_resolution(
    db: Session, user: models.User, payload: dict[str, Any]
) -> dict[str, Any]:
    incident = _incident(db, payload["incident_id"])
    approval = models.Approval(
        incident_id=incident.id,
        requested_by=user.id,
        action_type="mock_resolve_incident",
        resource_type="incident",
        resource_id=incident.id,
        status="pending",
        request_reason=(
            "Resolving an incident is a mock external-impacting action and requires approval."
        ),
    )
    db.add(approval)
    db.flush()
    timeline(
        db,
        incident_id=incident.id,
        event_type="approval.requested",
        title="Incident resolution awaiting approval",
        description=incident.title,
        actor_type="user",
        actor_id=user.id,
        metadata={"approval_id": approval.id},
    )
    return {"incident": serialize(incident), "approval": serialize(approval)}


TOOL_HANDLERS: dict[str, ToolFunc] = {
    "search-logs": search_logs,
    "search-runbooks": search_runbooks,
    "get-incident-details": get_incident_details,
    "get-service-health": get_service_health,
    "list-recent-service-changes": list_recent_service_changes,
    "get-related-incidents": get_related_incidents,
    "create-ticket-draft": create_ticket_draft,
    "draft-status-update": draft_status_update,
    "request-incident-resolution": request_incident_resolution,
}


def execute_tool(
    db: Session, user: models.User, tool_name: str, payload: dict[str, Any]
) -> dict[str, Any]:
    tool = db.scalar(select(models.MCPTool).where(models.MCPTool.name == tool_name))
    if not tool:
        raise HTTPException(status_code=404, detail="Tool not registered")
    if not tool.is_enabled:
        raise HTTPException(status_code=403, detail="Tool disabled by governance policy")
    if not role_allows(user.role, tool.permission_level):
        security_event(
            db,
            user_id=user.id,
            event_type="tool_permission_denied",
            severity="medium",
            resource_type="mcp_tool",
            resource_id=tool.id,
            details={
                "tool": tool_name,
                "required_role": tool.permission_level,
                "actual_role": user.role,
            },
        )
        db.commit()
        raise HTTPException(status_code=403, detail="Insufficient role for tool")
    handler = TOOL_HANDLERS[tool_name]
    started = time.perf_counter()
    status = "success"
    output: dict[str, Any] = {}
    error_message: str | None = None
    try:
        output = handler(db, user, payload)
    except Exception as exc:
        status = "error"
        error_message = str(exc)
        raise
    finally:
        latency_ms = int((time.perf_counter() - started) * 1000)
        call = models.ToolCall(
            incident_id=payload.get("incident_id"),
            tool_id=tool.id,
            tool_name=tool.name,
            called_by=user.id,
            input_json=payload,
            output_json=output,
            status=status,
            latency_ms=latency_ms,
            error_message=error_message,
        )
        db.add(call)
        audit(
            db,
            user_id=user.id,
            action=f"mcp.{tool_name}",
            resource_type="mcp_tool",
            resource_id=tool.id,
            metadata={"status": status, "latency_ms": latency_ms},
        )
        db.commit()
    return output


# Never expose secret columns via the generic serializer. serialize() is used
# by /auth/register, /auth/login, /auth/me and /admin endpoints, so leaking
# these would disclose password hashes and tokens in API responses.
_SENSITIVE_FIELDS = {"hashed_password", "password", "password_hash", "secret", "token", "api_key"}


def serialize(row: Any) -> dict[str, Any]:
    if row is None:
        return {}
    result = {}
    for key, value in row.__dict__.items():
        if key.startswith("_") or key in _SENSITIVE_FIELDS:
            continue
        result[key] = value.isoformat() if hasattr(value, "isoformat") else value
    return result
