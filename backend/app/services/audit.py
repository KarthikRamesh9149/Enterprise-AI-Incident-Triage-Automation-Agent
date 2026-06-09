from sqlalchemy.orm import Session

from app.db import models


def audit(
    db: Session,
    *,
    user_id: str | None,
    action: str,
    resource_type: str,
    resource_id: str | None = None,
    metadata: dict | None = None,
) -> models.AuditLog:
    row = models.AuditLog(
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        event_metadata_json=metadata or {},
    )
    db.add(row)
    return row


def security_event(
    db: Session,
    *,
    user_id: str | None,
    event_type: str,
    severity: str,
    resource_type: str,
    resource_id: str | None = None,
    details: dict | None = None,
) -> models.SecurityEvent:
    row = models.SecurityEvent(
        user_id=user_id,
        event_type=event_type,
        severity=severity,
        resource_type=resource_type,
        resource_id=resource_id,
        details_json=details or {},
    )
    db.add(row)
    return row


def timeline(
    db: Session,
    *,
    incident_id: str,
    event_type: str,
    title: str,
    description: str,
    actor_type: str = "system",
    actor_id: str | None = None,
    metadata: dict | None = None,
) -> models.IncidentTimelineEvent:
    row = models.IncidentTimelineEvent(
        incident_id=incident_id,
        event_type=event_type,
        title=title,
        description=description,
        actor_type=actor_type,
        actor_id=actor_id,
        metadata_json=metadata or {},
    )
    db.add(row)
    return row
