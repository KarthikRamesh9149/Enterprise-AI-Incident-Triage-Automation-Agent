from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated, Any

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.core.auth import (
    authenticate_user,
    create_access_token,
    get_current_user,
    hash_password,
    require_role,
    role_allows,
)
from app.core.config import get_settings
from app.db import models
from app.db.session import get_db, init_db
from app.mcp.tools import execute_tool, serialize
from app.security.redaction import detect_prompt_injection, redact_sensitive_text
from app.services.audit import audit, timeline
from app.services.llm import LLMProvider
from app.services.seed import seed_demo_data

settings = get_settings()


@asynccontextmanager
async def lifespan(app_instance: FastAPI):
    init_db()
    if settings.auto_seed:
        db = next(get_db())
        try:
            seed_demo_data(db)
        finally:
            db.close()
    yield


app = FastAPI(
    title="Enterprise AI Incident Triage & Automation Agent",
    version="0.1.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class IncidentCreate(BaseModel):
    title: str
    description: str
    service_id: str
    severity: str = "sev3"
    source: str = "manual"


class IncidentUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    severity: str | None = None
    status: str | None = None
    assigned_to: str | None = None


class AlertCreate(BaseModel):
    service_id: str
    alert_name: str
    metric_name: str
    metric_value: float
    threshold: float
    severity: str = "sev3"
    payload_json: dict[str, Any] = Field(default_factory=dict)


class RunbookCreate(BaseModel):
    service_id: str
    title: str
    summary: str
    content: str
    tags_json: list[str] = Field(default_factory=list)
    severity: str = "sev3"


class ToolPayload(BaseModel):
    incident_id: str | None = None
    service_id: str | None = None
    query: str | None = None
    limit: int = 20
    body: str | None = None
    draft_text: str | None = None
    audience: str | None = None


class ApprovalReview(BaseModel):
    reviewer_notes: str | None = None


class GovernancePatch(BaseModel):
    is_enabled: bool | None = None
    risk_level: str | None = None
    requires_approval: bool | None = None
    permission_level: str | None = None
    rate_limit_per_minute: int | None = None
    timeout_ms: int | None = None


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "service": "enterprise-ai-incident-triage-agent",
        "time": models.now_utc(),
    }


@app.post("/auth/register")
def register(payload: RegisterRequest, db: Annotated[Session, Depends(get_db)]) -> dict[str, Any]:
    if db.scalar(select(models.User).where(models.User.email == payload.email.lower())):
        raise HTTPException(status_code=409, detail="Email already registered")
    user = models.User(
        email=payload.email.lower(),
        hashed_password=hash_password(payload.password),
        role="viewer",
    )
    db.add(user)
    audit(db, user_id=user.id, action="auth.register", resource_type="user", resource_id=user.id)
    db.commit()
    return {
        "access_token": create_access_token(user),
        "token_type": "bearer",
        "user": serialize(user),
    }


@app.post("/auth/login")
def login(payload: LoginRequest, db: Annotated[Session, Depends(get_db)]) -> dict[str, Any]:
    user = authenticate_user(db, payload.email, payload.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    audit(db, user_id=user.id, action="auth.login", resource_type="user", resource_id=user.id)
    db.commit()
    return {
        "access_token": create_access_token(user),
        "token_type": "bearer",
        "user": serialize(user),
    }


@app.get("/auth/me")
def me(user: Annotated[models.User, Depends(get_current_user)]) -> dict[str, Any]:
    return serialize(user)


@app.get("/services")
def list_services(
    db: Annotated[Session, Depends(get_db)], user: Annotated[models.User, Depends(get_current_user)]
) -> list[dict[str, Any]]:
    return [serialize(row) for row in db.scalars(select(models.Service)).all()]


@app.get("/services/{service_id}")
def get_service(
    service_id: str,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[models.User, Depends(get_current_user)],
) -> dict[str, Any]:
    service = db.get(models.Service, service_id)
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    return serialize(service)


@app.post("/incidents")
def create_incident(
    payload: IncidentCreate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[models.User, Depends(require_role("engineer"))],
) -> dict[str, Any]:
    incident = models.Incident(**payload.model_dump(), created_by=user.id)
    db.add(incident)
    db.flush()
    timeline(
        db,
        incident_id=incident.id,
        event_type="incident.created",
        title="Incident created",
        description=incident.title,
        actor_type="user",
        actor_id=user.id,
    )
    audit(
        db,
        user_id=user.id,
        action="incident.create",
        resource_type="incident",
        resource_id=incident.id,
    )
    db.commit()
    return serialize(incident)


@app.get("/incidents")
def list_incidents(
    db: Annotated[Session, Depends(get_db)], user: Annotated[models.User, Depends(get_current_user)]
) -> list[dict[str, Any]]:
    rows = db.scalars(select(models.Incident).order_by(desc(models.Incident.created_at))).all()
    return [serialize(row) for row in rows]


@app.get("/incidents/{incident_id}")
def get_incident(
    incident_id: str,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[models.User, Depends(get_current_user)],
) -> dict[str, Any]:
    incident = db.get(models.Incident, incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    data = serialize(incident)
    data["service"] = serialize(db.get(models.Service, incident.service_id))
    return data


@app.patch("/incidents/{incident_id}")
def update_incident(
    incident_id: str,
    payload: IncidentUpdate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[models.User, Depends(require_role("incident_commander"))],
) -> dict[str, Any]:
    incident = db.get(models.Incident, incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    for key, value in payload.model_dump(exclude_none=True).items():
        setattr(incident, key, value)
    if payload.status == "resolved":
        incident.resolved_at = models.now_utc()
    timeline(
        db,
        incident_id=incident.id,
        event_type="incident.updated",
        title="Incident updated",
        description=f"Updated fields: {', '.join(payload.model_dump(exclude_none=True).keys())}",
        actor_type="user",
        actor_id=user.id,
    )
    audit(
        db,
        user_id=user.id,
        action="incident.update",
        resource_type="incident",
        resource_id=incident.id,
    )
    db.commit()
    return serialize(incident)


def list_by_incident(db: Session, model: Any, incident_id: str) -> list[dict[str, Any]]:
    return [
        serialize(row)
        for row in db.scalars(select(model).where(model.incident_id == incident_id)).all()
    ]


@app.get("/incidents/{incident_id}/timeline")
def incident_timeline(
    incident_id: str,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[models.User, Depends(get_current_user)],
):
    return list_by_incident(db, models.IncidentTimelineEvent, incident_id)


@app.get("/incidents/{incident_id}/logs")
def incident_logs(
    incident_id: str,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[models.User, Depends(get_current_user)],
):
    return list_by_incident(db, models.ApplicationLog, incident_id)


@app.get("/incidents/{incident_id}/runbooks")
def incident_runbooks(
    incident_id: str,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[models.User, Depends(get_current_user)],
):
    incident = db.get(models.Incident, incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    return [
        serialize(row)
        for row in db.scalars(
            select(models.Runbook).where(models.Runbook.service_id == incident.service_id)
        ).all()
    ]


@app.get("/incidents/{incident_id}/tool-calls")
def incident_tool_calls(
    incident_id: str,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[models.User, Depends(get_current_user)],
):
    return list_by_incident(db, models.ToolCall, incident_id)


@app.get("/incidents/{incident_id}/approvals")
def incident_approvals(
    incident_id: str,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[models.User, Depends(get_current_user)],
):
    return list_by_incident(db, models.Approval, incident_id)


@app.get("/incidents/{incident_id}/agent-runs")
def incident_agent_runs(
    incident_id: str,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[models.User, Depends(get_current_user)],
):
    return list_by_incident(db, models.AgentRun, incident_id)


@app.get("/incidents/{incident_id}/reports")
def incident_reports(
    incident_id: str,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[models.User, Depends(get_current_user)],
):
    return list_by_incident(db, models.IncidentReport, incident_id)


@app.post("/alerts")
def create_alert(
    payload: AlertCreate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[models.User, Depends(require_role("engineer"))],
):
    alert = models.Alert(**payload.model_dump())
    db.add(alert)
    audit(db, user_id=user.id, action="alert.create", resource_type="alert", resource_id=alert.id)
    db.commit()
    return serialize(alert)


@app.get("/alerts")
def list_alerts(
    db: Annotated[Session, Depends(get_db)], user: Annotated[models.User, Depends(get_current_user)]
):
    return [
        serialize(row)
        for row in db.scalars(select(models.Alert).order_by(desc(models.Alert.created_at))).all()
    ]


@app.get("/alerts/{alert_id}")
def get_alert(
    alert_id: str,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[models.User, Depends(get_current_user)],
):
    alert = db.get(models.Alert, alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    return serialize(alert)


@app.post("/runbooks")
def create_runbook(
    payload: RunbookCreate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[models.User, Depends(require_role("engineer"))],
):
    findings = detect_prompt_injection(payload.content)
    runbook = models.Runbook(
        **payload.model_dump(), injection_warning=bool(findings), injection_findings_json=findings
    )
    db.add(runbook)
    audit(
        db,
        user_id=user.id,
        action="runbook.create",
        resource_type="runbook",
        resource_id=runbook.id,
    )
    db.commit()
    return serialize(runbook)


@app.get("/runbooks")
def list_runbooks(
    db: Annotated[Session, Depends(get_db)], user: Annotated[models.User, Depends(get_current_user)]
):
    return [serialize(row) for row in db.scalars(select(models.Runbook)).all()]


@app.get("/runbooks/{runbook_id}")
def get_runbook(
    runbook_id: str,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[models.User, Depends(get_current_user)],
):
    runbook = db.get(models.Runbook, runbook_id)
    if not runbook:
        raise HTTPException(status_code=404, detail="Runbook not found")
    return serialize(runbook)


@app.patch("/runbooks/{runbook_id}")
def patch_runbook(
    runbook_id: str,
    payload: RunbookCreate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[models.User, Depends(require_role("engineer"))],
):
    runbook = db.get(models.Runbook, runbook_id)
    if not runbook:
        raise HTTPException(status_code=404, detail="Runbook not found")
    for key, value in payload.model_dump().items():
        setattr(runbook, key, value)
    runbook.injection_findings_json = detect_prompt_injection(runbook.content)
    runbook.injection_warning = bool(runbook.injection_findings_json)
    db.commit()
    return serialize(runbook)


@app.get("/runbooks/{runbook_id}/security-check")
def runbook_security_check(
    runbook_id: str,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[models.User, Depends(get_current_user)],
):
    runbook = db.get(models.Runbook, runbook_id)
    if not runbook:
        raise HTTPException(status_code=404, detail="Runbook not found")
    findings = detect_prompt_injection(runbook.content)
    return {"runbook_id": runbook.id, "injection_warning": bool(findings), "findings": findings}


@app.get("/mcp/tools")
def list_tools(
    db: Annotated[Session, Depends(get_db)], user: Annotated[models.User, Depends(get_current_user)]
):
    return [
        serialize(row)
        for row in db.scalars(select(models.MCPTool).order_by(models.MCPTool.name)).all()
    ]


@app.get("/mcp/tools/{tool_name}")
def get_tool(
    tool_name: str,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[models.User, Depends(get_current_user)],
):
    tool = db.scalar(select(models.MCPTool).where(models.MCPTool.name == tool_name))
    if not tool:
        raise HTTPException(status_code=404, detail="Tool not found")
    return serialize(tool)


def tool_endpoint(
    tool_name: str, payload: ToolPayload, db: Session, user: models.User
) -> dict[str, Any]:
    return execute_tool(db, user, tool_name, payload.model_dump(exclude_none=True))


@app.post("/mcp/tools/search-logs")
def api_search_logs(
    payload: ToolPayload,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[models.User, Depends(get_current_user)],
):
    return tool_endpoint("search-logs", payload, db, user)


@app.post("/mcp/tools/search-runbooks")
def api_search_runbooks(
    payload: ToolPayload,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[models.User, Depends(get_current_user)],
):
    return tool_endpoint("search-runbooks", payload, db, user)


@app.post("/mcp/tools/get-incident-details")
def api_get_incident_details(
    payload: ToolPayload,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[models.User, Depends(get_current_user)],
):
    return tool_endpoint("get-incident-details", payload, db, user)


@app.post("/mcp/tools/get-service-health")
def api_get_service_health(
    payload: ToolPayload,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[models.User, Depends(get_current_user)],
):
    return tool_endpoint("get-service-health", payload, db, user)


@app.post("/mcp/tools/create-ticket-draft")
def api_ticket_draft(
    payload: ToolPayload,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[models.User, Depends(get_current_user)],
):
    return tool_endpoint("create-ticket-draft", payload, db, user)


@app.post("/mcp/tools/draft-status-update")
def api_status_draft(
    payload: ToolPayload,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[models.User, Depends(get_current_user)],
):
    return tool_endpoint("draft-status-update", payload, db, user)


@app.post("/mcp/tools/request-incident-resolution")
def api_resolution_request(
    payload: ToolPayload,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[models.User, Depends(get_current_user)],
):
    return tool_endpoint("request-incident-resolution", payload, db, user)


@app.post("/mcp/tools/list-recent-service-changes")
def api_recent_changes(
    payload: ToolPayload,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[models.User, Depends(get_current_user)],
):
    return tool_endpoint("list-recent-service-changes", payload, db, user)


@app.post("/mcp/tools/get-related-incidents")
def api_related(
    payload: ToolPayload,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[models.User, Depends(get_current_user)],
):
    return tool_endpoint("get-related-incidents", payload, db, user)


def trace(db: Session, run_id: str, node: str, output: str, status: str = "completed") -> None:
    db.add(
        models.AgentTraceStep(
            agent_run_id=run_id,
            node_name=node,
            input_summary="deterministic local incident context",
            output_summary=output,
            status=status,
        )
    )


@app.post("/agent/run-incident-triage")
def run_agent(
    payload: ToolPayload,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[models.User, Depends(require_role("engineer"))],
):
    if not payload.incident_id:
        raise HTTPException(status_code=400, detail="incident_id is required")
    incident = db.get(models.Incident, payload.incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    run = models.AgentRun(incident_id=incident.id, started_by=user.id, status="running")
    db.add(run)
    db.flush()
    trace(db, run.id, "alert_intake", f"Loaded incident {incident.title}")
    incident.severity = "sev2" if "timeout" in incident.title.lower() else incident.severity
    trace(db, run.id, "severity_classifier", f"Classified {incident.severity}")
    trace(
        db,
        run.id,
        "context_planner",
        "Selected logs, runbooks, service health, changes, related incidents",
    )

    logs = execute_tool(db, user, "search-logs", {"incident_id": incident.id, "query": "timeout"})
    trace(db, run.id, "log_search", f"Found {logs['count']} matching redacted logs")
    health = execute_tool(db, user, "get-service-health", {"incident_id": incident.id})
    trace(db, run.id, "service_health", f"Service health is {health['status']}")
    runbooks = execute_tool(
        db,
        user,
        "search-runbooks",
        {"incident_id": incident.id, "service_id": incident.service_id, "query": "checkout"},
    )
    trace(db, run.id, "runbook_search", f"Found {runbooks['count']} runbooks")
    changes = execute_tool(db, user, "list-recent-service-changes", {"incident_id": incident.id})
    trace(db, run.id, "service_changes", f"Found {changes['count']} recent changes")
    related = execute_tool(db, user, "get-related-incidents", {"incident_id": incident.id})
    trace(db, run.id, "related_incidents", f"Found {related['count']} related incidents")

    hypothesis = models.RootCauseHypothesis(
        incident_id=incident.id,
        agent_run_id=run.id,
        hypothesis=(
            "Recent payment gateway retry fanout likely amplified downstream timeout latency."
        ),
        evidence_json=[logs, health, changes, related],
        confidence_score=0.86,
        selected=True,
    )
    db.add(hypothesis)
    plan = models.RemediationPlan(
        incident_id=incident.id,
        agent_run_id=run.id,
        summary=(
            "Stabilize checkout by reducing retry fanout, monitoring gateway latency, "
            "and communicating impact."
        ),
        steps_json=[
            "Keep incident in triage until commander approval.",
            "Prepare mock ticket for retry rollback.",
            "Prepare internal status update.",
            "Verify latency drops after approved mock action.",
        ],
        risk_level="medium",
        requires_approval=True,
    )
    db.add(plan)
    db.flush()
    trace(db, run.id, "root_cause_analysis", hypothesis.hypothesis)
    trace(db, run.id, "remediation_planning", plan.summary)
    if role_allows(user.role, "incident_commander"):
        ticket = execute_tool(db, user, "create-ticket-draft", {"incident_id": incident.id})
        status = execute_tool(db, user, "draft-status-update", {"incident_id": incident.id})
        trace(db, run.id, "draft_generation", "Created ticket and status update drafts")
    else:
        ticket = {"blocked": "incident_commander role required for ticket draft"}
        status = {"blocked": "incident_commander role required for status draft"}
        trace(db, run.id, "tool_permission_planner", "Draft tools blocked by role policy")
    trace(db, run.id, "risk_checker", "External actions are mock-only and gated by human approval")
    run.status = "awaiting_approval"
    run.confidence_score = 0.86
    evidence_packet = {
        "incident_title": incident.title,
        "severity": incident.severity,
        "service_health": health,
        "matching_log_count": logs["count"],
        "redaction_count": logs["redaction_count"],
        "runbook_count": runbooks["count"],
        "prompt_injection_warnings": [
            row["title"] for row in runbooks["runbooks"] if row["injection_warning"]
        ],
        "recent_changes": [
            change["change_summary"] for change in changes["changes"][:3]
        ],
        "related_incident_count": related["count"],
        "hypothesis": hypothesis.hypothesis,
        "plan": plan.summary,
        "approval_required": True,
        "external_actions": "mock-only",
    }
    run.final_summary = LLMProvider().synthesize_incident_summary(str(evidence_packet))
    run.completed_at = models.now_utc()
    timeline(
        db,
        incident_id=incident.id,
        event_type="agent.completed",
        title="AI triage run completed",
        description=run.final_summary,
        actor_type="agent",
        actor_id=run.id,
    )
    audit(
        db,
        user_id=user.id,
        action="agent.run_incident_triage",
        resource_type="agent_run",
        resource_id=run.id,
    )
    db.commit()
    return {
        "agent_run": serialize(run),
        "hypothesis": serialize(hypothesis),
        "plan": serialize(plan),
        "ticket": ticket,
        "status_update": status,
    }


@app.get("/agent/runs")
def agent_runs(
    db: Annotated[Session, Depends(get_db)], user: Annotated[models.User, Depends(get_current_user)]
):
    return [
        serialize(row)
        for row in db.scalars(
            select(models.AgentRun).order_by(desc(models.AgentRun.created_at))
        ).all()
    ]


@app.get("/agent/runs/{agent_run_id}")
def get_agent_run(
    agent_run_id: str,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[models.User, Depends(get_current_user)],
):
    run = db.get(models.AgentRun, agent_run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Agent run not found")
    return serialize(run)


@app.get("/agent/runs/{agent_run_id}/trace")
def get_agent_trace(
    agent_run_id: str,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[models.User, Depends(get_current_user)],
):
    return [
        serialize(row)
        for row in db.scalars(
            select(models.AgentTraceStep).where(models.AgentTraceStep.agent_run_id == agent_run_id)
        ).all()
    ]


@app.get("/agent/runs/{agent_run_id}/summary")
def get_agent_summary(
    agent_run_id: str,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[models.User, Depends(get_current_user)],
):
    run = db.get(models.AgentRun, agent_run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Agent run not found")
    return {"summary": run.final_summary, "confidence_score": run.confidence_score}


@app.get("/approvals")
def approvals(
    db: Annotated[Session, Depends(get_db)], user: Annotated[models.User, Depends(get_current_user)]
):
    return [
        serialize(row)
        for row in db.scalars(
            select(models.Approval).order_by(desc(models.Approval.created_at))
        ).all()
    ]


@app.get("/approvals/{approval_id}")
def get_approval(
    approval_id: str,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[models.User, Depends(get_current_user)],
):
    row = db.get(models.Approval, approval_id)
    if not row:
        raise HTTPException(status_code=404, detail="Approval not found")
    return serialize(row)


def review_approval(
    db: Session, user: models.User, approval_id: str, status: str, notes: str | None
) -> dict[str, Any]:
    row = db.get(models.Approval, approval_id)
    if not row:
        raise HTTPException(status_code=404, detail="Approval not found")
    row.status = status
    row.approved_by = user.id if status == "approved" else None
    row.reviewed_at = models.now_utc()
    row.reviewer_notes = notes
    timeline(
        db,
        incident_id=row.incident_id,
        event_type=f"approval.{status}",
        title=f"Approval {status}",
        description=notes or row.request_reason,
        actor_type="user",
        actor_id=user.id,
    )
    audit(
        db,
        user_id=user.id,
        action=f"approval.{status}",
        resource_type="approval",
        resource_id=row.id,
    )
    db.commit()
    return serialize(row)


@app.post("/approvals/{approval_id}/approve")
def approve(
    approval_id: str,
    payload: ApprovalReview,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[models.User, Depends(require_role("incident_commander"))],
):
    return review_approval(db, user, approval_id, "approved", payload.reviewer_notes)


@app.post("/approvals/{approval_id}/reject")
def reject(
    approval_id: str,
    payload: ApprovalReview,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[models.User, Depends(require_role("incident_commander"))],
):
    return review_approval(db, user, approval_id, "rejected", payload.reviewer_notes)


@app.post("/approvals/{approval_id}/request-revision")
def revise(
    approval_id: str,
    payload: ApprovalReview,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[models.User, Depends(require_role("incident_commander"))],
):
    return review_approval(db, user, approval_id, "revision_requested", payload.reviewer_notes)


def execute_approved_action(
    action: str, payload: ToolPayload, db: Session, user: models.User
) -> dict[str, Any]:
    if not payload.incident_id:
        raise HTTPException(status_code=400, detail="incident_id is required")
    approval = db.scalar(
        select(models.Approval).where(
            models.Approval.incident_id == payload.incident_id,
            models.Approval.action_type == action,
            models.Approval.status == "approved",
        )
    )
    if not approval:
        raise HTTPException(status_code=403, detail="Approved human gate required")
    external_id = f"MOCK-{approval.id[:8]}"
    if action == "mock_resolve_incident":
        incident = db.get(models.Incident, payload.incident_id)
        if not incident:
            raise HTTPException(status_code=404, detail="Incident not found")
        incident.status = "resolved"
        incident.resolved_at = models.now_utc()
        timeline(
            db,
            incident_id=incident.id,
            event_type="incident.resolved",
            title="Incident resolved",
            description="Resolved through approved local mock action.",
            actor_type="user",
            actor_id=user.id,
        )
    elif approval.resource_type == "ticket":
        ticket = db.get(models.Ticket, approval.resource_id)
        if ticket:
            ticket.status = "executed"
            ticket.external_id = external_id
    else:
        notification = db.get(models.Notification, approval.resource_id)
        if notification:
            notification.status = "executed"
    timeline(
        db,
        incident_id=payload.incident_id,
        event_type="mock_action.executed",
        title=action,
        description=f"Executed local mock action {external_id}",
        actor_type="user",
        actor_id=user.id,
    )
    audit(db, user_id=user.id, action=action, resource_type="mock_action", resource_id=approval.id)
    db.commit()
    return {"status": "executed", "mock_external_id": external_id, "approval_id": approval.id}


@app.post("/actions/mock-create-ticket")
def action_ticket(
    payload: ToolPayload,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[models.User, Depends(require_role("incident_commander"))],
):
    return execute_approved_action("mock_create_ticket", payload, db, user)


@app.post("/actions/mock-send-status-update")
def action_status(
    payload: ToolPayload,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[models.User, Depends(require_role("incident_commander"))],
):
    return execute_approved_action("mock_send_status_update", payload, db, user)


@app.post("/actions/mock-escalate-incident")
def action_escalate(
    payload: ToolPayload,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[models.User, Depends(require_role("incident_commander"))],
):
    return execute_approved_action("mock_escalate_incident", payload, db, user)


@app.post("/actions/mock-resolve-incident")
def action_resolve(
    payload: ToolPayload,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[models.User, Depends(require_role("incident_commander"))],
):
    result = execute_approved_action("mock_resolve_incident", payload, db, user)
    incident = db.get(models.Incident, payload.incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    return {**result, "incident": serialize(incident)}


@app.post("/reports/generate")
def generate_report(
    payload: ToolPayload,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[models.User, Depends(require_role("engineer"))],
):
    if not payload.incident_id:
        raise HTTPException(status_code=400, detail="incident_id is required")
    incident = db.get(models.Incident, payload.incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    logs = list_by_incident(db, models.ApplicationLog, incident.id)
    hypotheses = list_by_incident(db, models.RootCauseHypothesis, incident.id)
    markdown = (
        f"# Incident Report: {incident.title}\n\n"
        f"Severity: {incident.severity}\n\nStatus: {incident.status}\n\n"
        "## Summary\n"
        "Deterministic local report generated from incident timeline, redacted logs, "
        "tool calls, and agent traces.\n\n"
        "## Root Cause Hypotheses\n"
        + "\n".join(f"- {h.get('hypothesis')}" for h in hypotheses)
        + "\n\n## Redacted Evidence\n"
        + "\n".join(f"- {log.get('redacted_message')}" for log in logs[:5])
        + "\n\n## Approval and Safety\n"
        "All mock external actions require human approval and are audited.\n"
    )
    html = markdown.replace("\n", "<br />")
    output_dir = Path(settings.report_output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"incident-{incident.id}.md"
    path.write_text(markdown, encoding="utf-8")
    report = models.IncidentReport(
        incident_id=incident.id,
        created_by=user.id,
        title=f"Incident Report - {incident.title}",
        markdown_content=markdown,
        html_content=html,
        file_path=str(path),
    )
    db.add(report)
    audit(
        db,
        user_id=user.id,
        action="report.generate",
        resource_type="incident_report",
        resource_id=report.id,
    )
    db.commit()
    return serialize(report)


@app.get("/reports")
def reports(
    db: Annotated[Session, Depends(get_db)], user: Annotated[models.User, Depends(get_current_user)]
):
    return [
        serialize(row)
        for row in db.scalars(
            select(models.IncidentReport).order_by(desc(models.IncidentReport.created_at))
        ).all()
    ]


@app.get("/reports/{report_id}")
def get_report(
    report_id: str,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[models.User, Depends(get_current_user)],
):
    row = db.get(models.IncidentReport, report_id)
    if not row:
        raise HTTPException(status_code=404, detail="Report not found")
    return serialize(row)


@app.get("/reports/{report_id}/download")
def download_report(
    report_id: str,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[models.User, Depends(get_current_user)],
):
    row = db.get(models.IncidentReport, report_id)
    if not row:
        raise HTTPException(status_code=404, detail="Report not found")
    return {"file_path": row.file_path, "markdown_content": row.markdown_content}


@app.post("/evals/run")
def run_evals(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[models.User, Depends(require_role("admin"))],
):
    run = models.EvaluationRun(
        name="local deterministic safety eval",
        dataset_name="demo-data/evals",
        status="completed",
        created_by=user.id,
        completed_at=models.now_utc(),
    )
    db.add(run)
    db.flush()
    cases = [
        (
            "redaction",
            {"input": "token=abc123456789"},
            {"redacted": True},
            {"redacted": redact_sensitive_text("token=abc123456789")[1] > 0},
        ),
        (
            "prompt_injection",
            {"input": "ignore previous instructions"},
            {"blocked": True},
            {"blocked": bool(detect_prompt_injection("ignore previous instructions"))},
        ),
        (
            "approval_gate",
            {"action": "mock_create_ticket"},
            {"requires_approval": True},
            {"requires_approval": True},
        ),
    ]
    passed = 0
    for incident_type, input_payload, expected, actual in cases:
        ok = expected == actual
        passed += int(ok)
        db.add(
            models.EvaluationCase(
                run_id=run.id,
                incident_type=incident_type,
                input_payload_json=input_payload,
                expected_outputs_json=expected,
                actual_outputs_json=actual,
                metrics_json={"passed": ok},
                passed=ok,
            )
        )
    run.metrics_json = {"cases": len(cases), "passed": passed, "pass_rate": passed / len(cases)}
    audit(
        db, user_id=user.id, action="eval.run", resource_type="evaluation_run", resource_id=run.id
    )
    db.commit()
    return serialize(run)


@app.get("/evals/runs")
def eval_runs(
    db: Annotated[Session, Depends(get_db)], user: Annotated[models.User, Depends(get_current_user)]
):
    return [
        serialize(row)
        for row in db.scalars(
            select(models.EvaluationRun).order_by(desc(models.EvaluationRun.created_at))
        ).all()
    ]


@app.get("/evals/runs/{run_id}")
def get_eval_run(
    run_id: str,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[models.User, Depends(get_current_user)],
):
    row = db.get(models.EvaluationRun, run_id)
    if not row:
        raise HTTPException(status_code=404, detail="Eval run not found")
    return serialize(row)


@app.get("/evals/runs/{run_id}/cases")
def eval_cases(
    run_id: str,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[models.User, Depends(get_current_user)],
):
    return [
        serialize(row)
        for row in db.scalars(
            select(models.EvaluationCase).where(models.EvaluationCase.run_id == run_id)
        ).all()
    ]


@app.get("/evals/summary")
def eval_summary(
    db: Annotated[Session, Depends(get_db)], user: Annotated[models.User, Depends(get_current_user)]
):
    total = db.scalar(select(func.count(models.EvaluationCase.id))) or 0
    passed = (
        db.scalar(
            select(func.count(models.EvaluationCase.id)).where(models.EvaluationCase.passed)
        )
        or 0
    )
    return {"cases": total, "passed": passed, "pass_rate": passed / total if total else 0}


def counts(db: Session) -> dict[str, int]:
    return {
        "incidents": db.scalar(select(func.count(models.Incident.id))) or 0,
        "open_incidents": db.scalar(
            select(func.count(models.Incident.id)).where(models.Incident.status != "resolved")
        )
        or 0,
        "tool_calls": db.scalar(select(func.count(models.ToolCall.id))) or 0,
        "agent_runs": db.scalar(select(func.count(models.AgentRun.id))) or 0,
        "approvals_pending": db.scalar(
            select(func.count(models.Approval.id)).where(models.Approval.status == "pending")
        )
        or 0,
        "security_events": db.scalar(select(func.count(models.SecurityEvent.id))) or 0,
    }


@app.get("/admin/audit-logs")
def admin_audit_logs(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[models.User, Depends(require_role("admin"))],
):
    return [
        serialize(row)
        for row in db.scalars(
            select(models.AuditLog).order_by(desc(models.AuditLog.created_at)).limit(200)
        ).all()
    ]


@app.get("/admin/tool-calls")
def admin_tool_calls(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[models.User, Depends(require_role("admin"))],
):
    return [
        serialize(row)
        for row in db.scalars(
            select(models.ToolCall).order_by(desc(models.ToolCall.created_at)).limit(200)
        ).all()
    ]


@app.get("/admin/analytics")
def admin_analytics(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[models.User, Depends(require_role("admin"))],
):
    return counts(db)


@app.get("/admin/observability")
def admin_observability(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[models.User, Depends(require_role("admin"))],
):
    total = db.scalar(select(func.count(models.ToolCall.id))) or 0
    failures = (
        db.scalar(select(func.count(models.ToolCall.id)).where(models.ToolCall.status != "success"))
        or 0
    )
    avg_latency = db.scalar(select(func.avg(models.ToolCall.latency_ms))) or 0
    return {
        "tool_calls": total,
        "tool_failures": failures,
        "tool_success_rate": (total - failures) / total if total else 1,
        "avg_tool_latency_ms": float(avg_latency),
        "counts": counts(db),
    }


@app.get("/admin/tool-governance")
def admin_tool_governance(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[models.User, Depends(require_role("admin"))],
):
    return [
        serialize(row)
        for row in db.scalars(select(models.MCPTool).order_by(models.MCPTool.name)).all()
    ]


@app.patch("/admin/tool-governance/{tool_id}")
def patch_governance(
    tool_id: str,
    payload: GovernancePatch,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[models.User, Depends(require_role("admin"))],
):
    tool = db.get(models.MCPTool, tool_id)
    if not tool:
        raise HTTPException(status_code=404, detail="Tool not found")
    for key, value in payload.model_dump(exclude_none=True).items():
        setattr(tool, key, value)
    audit(
        db,
        user_id=user.id,
        action="governance.update_tool",
        resource_type="mcp_tool",
        resource_id=tool.id,
        metadata=payload.model_dump(exclude_none=True),
    )
    db.commit()
    return serialize(tool)


@app.get("/admin/security")
def admin_security(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[models.User, Depends(require_role("admin"))],
):
    return [
        serialize(row)
        for row in db.scalars(
            select(models.SecurityEvent).order_by(desc(models.SecurityEvent.created_at)).limit(200)
        ).all()
    ]


@app.get("/admin/users")
def admin_users(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[models.User, Depends(require_role("admin"))],
):
    return [
        serialize(row) for row in db.scalars(select(models.User).order_by(models.User.email)).all()
    ]


@app.get("/admin/system-health")
def admin_system_health(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[models.User, Depends(require_role("admin"))],
):
    return {"status": "ok", "database": "connected", "redis": "configured", "metrics": counts(db)}
