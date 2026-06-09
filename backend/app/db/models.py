import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.db.session import Base

JsonType = JSON().with_variant(JSONB, "postgresql")


def uuid_str() -> str:
    return str(uuid.uuid4())


def now_utc() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc, onupdate=now_utc)


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(64), index=True)


class Service(Base, TimestampMixin):
    __tablename__ = "services"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    name: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    owner_team: Mapped[str] = mapped_column(String(120))
    tier: Mapped[str] = mapped_column(String(32))
    description: Mapped[str] = mapped_column(Text)


class Incident(Base, TimestampMixin):
    __tablename__ = "incidents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text)
    service_id: Mapped[str] = mapped_column(ForeignKey("services.id"), index=True)
    severity: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(64), default="open", index=True)
    source: Mapped[str] = mapped_column(String(64), default="manual")
    detected_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    assigned_to: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    service: Mapped[Service] = relationship()


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    incident_id: Mapped[str | None] = mapped_column(ForeignKey("incidents.id"), nullable=True)
    service_id: Mapped[str] = mapped_column(ForeignKey("services.id"), index=True)
    alert_name: Mapped[str] = mapped_column(String(255))
    metric_name: Mapped[str] = mapped_column(String(120))
    metric_value: Mapped[float] = mapped_column(Float)
    threshold: Mapped[float] = mapped_column(Float)
    severity: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(64), default="firing")
    payload_json: Mapped[dict] = mapped_column(JsonType, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc)


class ApplicationLog(Base):
    __tablename__ = "application_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    service_id: Mapped[str] = mapped_column(ForeignKey("services.id"), index=True)
    incident_id: Mapped[str | None] = mapped_column(ForeignKey("incidents.id"), nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=now_utc, index=True)
    level: Mapped[str] = mapped_column(String(32))
    message: Mapped[str] = mapped_column(Text)
    trace_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    span_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JsonType, default=dict)
    redacted_message: Mapped[str] = mapped_column(Text, default="")
    redaction_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc)


class Runbook(Base, TimestampMixin):
    __tablename__ = "runbooks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    service_id: Mapped[str] = mapped_column(ForeignKey("services.id"), index=True)
    title: Mapped[str] = mapped_column(String(255))
    summary: Mapped[str] = mapped_column(Text)
    content: Mapped[str] = mapped_column(Text)
    tags_json: Mapped[list] = mapped_column(JsonType, default=list)
    severity: Mapped[str] = mapped_column(String(32), default="sev3")
    trust_score: Mapped[float] = mapped_column(Float, default=1.0)
    injection_warning: Mapped[bool] = mapped_column(Boolean, default=False)
    injection_findings_json: Mapped[list] = mapped_column(JsonType, default=list)


class ServiceChange(Base):
    __tablename__ = "service_changes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    service_id: Mapped[str] = mapped_column(ForeignKey("services.id"), index=True)
    change_id: Mapped[str] = mapped_column(String(120))
    commit_hash: Mapped[str] = mapped_column(String(80))
    changed_by: Mapped[str] = mapped_column(String(255))
    changed_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc)
    change_summary: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(64))
    metadata_json: Mapped[dict] = mapped_column(JsonType, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc)


class RelatedIncident(Base):
    __tablename__ = "related_incidents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    source_incident_id: Mapped[str] = mapped_column(ForeignKey("incidents.id"), index=True)
    related_incident_id: Mapped[str] = mapped_column(ForeignKey("incidents.id"))
    service_id: Mapped[str] = mapped_column(ForeignKey("services.id"))
    similarity_reason: Mapped[str] = mapped_column(Text)
    resolution_summary: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc)


class Ticket(Base):
    __tablename__ = "tickets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    incident_id: Mapped[str] = mapped_column(ForeignKey("incidents.id"), index=True)
    title: Mapped[str] = mapped_column(String(255))
    body: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(64), default="draft")
    external_system: Mapped[str] = mapped_column(String(64), default="mock")
    external_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    created_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    approved_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    incident_id: Mapped[str] = mapped_column(ForeignKey("incidents.id"), index=True)
    channel: Mapped[str] = mapped_column(String(64), default="mock-status")
    audience: Mapped[str] = mapped_column(String(120), default="internal")
    draft_text: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(64), default="draft")
    created_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    approved_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class MCPTool(Base, TimestampMixin):
    __tablename__ = "mcp_tools"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    name: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    description: Mapped[str] = mapped_column(Text)
    input_schema_json: Mapped[dict] = mapped_column(JsonType, default=dict)
    output_schema_json: Mapped[dict] = mapped_column(JsonType, default=dict)
    permission_level: Mapped[str] = mapped_column(String(64), default="engineer")
    risk_level: Mapped[str] = mapped_column(String(32), default="low")
    requires_approval: Mapped[bool] = mapped_column(Boolean, default=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    timeout_ms: Mapped[int] = mapped_column(Integer, default=5000)
    rate_limit_per_minute: Mapped[int] = mapped_column(Integer, default=60)


class ToolCall(Base):
    __tablename__ = "tool_calls"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    incident_id: Mapped[str | None] = mapped_column(ForeignKey("incidents.id"), nullable=True)
    tool_id: Mapped[str | None] = mapped_column(ForeignKey("mcp_tools.id"), nullable=True)
    tool_name: Mapped[str] = mapped_column(String(120), index=True)
    called_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    input_json: Mapped[dict] = mapped_column(JsonType, default=dict)
    output_json: Mapped[dict] = mapped_column(JsonType, default=dict)
    status: Mapped[str] = mapped_column(String(64))
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc)


class AgentRun(Base):
    __tablename__ = "agent_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    incident_id: Mapped[str] = mapped_column(ForeignKey("incidents.id"), index=True)
    started_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(64), default="running")
    confidence_score: Mapped[float] = mapped_column(Float, default=0)
    final_summary: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class AgentTraceStep(Base):
    __tablename__ = "agent_trace_steps"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    agent_run_id: Mapped[str] = mapped_column(ForeignKey("agent_runs.id"), index=True)
    node_name: Mapped[str] = mapped_column(String(120))
    input_summary: Mapped[str] = mapped_column(Text)
    output_summary: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(64), default="completed")
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc)


class RootCauseHypothesis(Base):
    __tablename__ = "root_cause_hypotheses"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    incident_id: Mapped[str] = mapped_column(ForeignKey("incidents.id"), index=True)
    agent_run_id: Mapped[str | None] = mapped_column(ForeignKey("agent_runs.id"), nullable=True)
    hypothesis: Mapped[str] = mapped_column(Text)
    evidence_json: Mapped[list] = mapped_column(JsonType, default=list)
    confidence_score: Mapped[float] = mapped_column(Float, default=0.0)
    selected: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc)


class RemediationPlan(Base):
    __tablename__ = "remediation_plans"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    incident_id: Mapped[str] = mapped_column(ForeignKey("incidents.id"), index=True)
    agent_run_id: Mapped[str | None] = mapped_column(ForeignKey("agent_runs.id"), nullable=True)
    summary: Mapped[str] = mapped_column(Text)
    steps_json: Mapped[list] = mapped_column(JsonType, default=list)
    risk_level: Mapped[str] = mapped_column(String(32), default="medium")
    requires_approval: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc)


class Approval(Base):
    __tablename__ = "approvals"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    incident_id: Mapped[str] = mapped_column(ForeignKey("incidents.id"), index=True)
    requested_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    approved_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    action_type: Mapped[str] = mapped_column(String(120))
    resource_type: Mapped[str] = mapped_column(String(120))
    resource_id: Mapped[str] = mapped_column(String(36))
    status: Mapped[str] = mapped_column(String(64), default="pending")
    request_reason: Mapped[str] = mapped_column(Text)
    reviewer_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class IncidentTimelineEvent(Base):
    __tablename__ = "incident_timeline_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    incident_id: Mapped[str] = mapped_column(ForeignKey("incidents.id"), index=True)
    event_type: Mapped[str] = mapped_column(String(120))
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text)
    actor_type: Mapped[str] = mapped_column(String(64), default="system")
    actor_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JsonType, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc)


class IncidentReport(Base):
    __tablename__ = "incident_reports"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    incident_id: Mapped[str] = mapped_column(ForeignKey("incidents.id"), index=True)
    created_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(255))
    markdown_content: Mapped[str] = mapped_column(Text)
    html_content: Mapped[str] = mapped_column(Text)
    file_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc)


class EvaluationRun(Base):
    __tablename__ = "evaluation_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    name: Mapped[str] = mapped_column(String(255))
    dataset_name: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(64), default="running")
    metrics_json: Mapped[dict] = mapped_column(JsonType, default=dict)
    created_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class EvaluationCase(Base):
    __tablename__ = "evaluation_cases"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    run_id: Mapped[str] = mapped_column(ForeignKey("evaluation_runs.id"), index=True)
    incident_type: Mapped[str] = mapped_column(String(120))
    input_payload_json: Mapped[dict] = mapped_column(JsonType, default=dict)
    expected_outputs_json: Mapped[dict] = mapped_column(JsonType, default=dict)
    actual_outputs_json: Mapped[dict] = mapped_column(JsonType, default=dict)
    metrics_json: Mapped[dict] = mapped_column(JsonType, default=dict)
    passed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    action: Mapped[str] = mapped_column(String(160), index=True)
    resource_type: Mapped[str] = mapped_column(String(120))
    resource_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    event_metadata_json: Mapped[dict] = mapped_column(JsonType, default=dict)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc)


class SecurityEvent(Base):
    __tablename__ = "security_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    event_type: Mapped[str] = mapped_column(String(120), index=True)
    severity: Mapped[str] = mapped_column(String(32))
    resource_type: Mapped[str] = mapped_column(String(120))
    resource_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    details_json: Mapped[dict] = mapped_column(JsonType, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc)


class SystemMetric(Base):
    __tablename__ = "system_metrics"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    metric_name: Mapped[str] = mapped_column(String(120), index=True)
    metric_value: Mapped[float] = mapped_column(Float)
    labels_json: Mapped[dict] = mapped_column(JsonType, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc)
