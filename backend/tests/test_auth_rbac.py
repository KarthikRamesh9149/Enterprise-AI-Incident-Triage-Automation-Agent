from pathlib import Path

import pytest
from pydantic import ValidationError

from app.core.config import Settings
from app.services.seed import DEMO_PASSWORD


def test_login_and_me(client):
    response = client.post(
        "/auth/login", json={"email": "engineer@example.com", "password": DEMO_PASSWORD}
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    me = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["role"] == "engineer"


def test_browser_session_is_http_only_and_does_not_require_bearer(client):
    response = client.post(
        "/auth/login", json={"email": "engineer@example.com", "password": DEMO_PASSWORD}
    )
    cookie = response.headers["set-cookie"].lower()
    assert "incident_agent_session=" in cookie
    assert "httponly" in cookie
    assert "samesite=strict" in cookie
    assert client.get("/auth/me").status_code == 200


def test_cookie_authenticated_write_rejects_untrusted_origin(client, incident_id):
    response = client.post(
        "/auth/login", json={"email": "engineer@example.com", "password": DEMO_PASSWORD}
    )
    assert response.status_code == 200
    rejected = client.post(
        "/mcp/tools/search-logs",
        headers={"Origin": "https://attacker.invalid"},
        json={"incident_id": incident_id, "query": "timeout"},
    )
    assert rejected.status_code == 403
    assert rejected.json()["detail"] == "Untrusted origin"


def test_production_configuration_requires_explicit_secret():
    with pytest.raises(ValidationError, match="JWT_SECRET is required"):
        Settings(
            _env_file=None,
            app_env="production",
            local_demo_mode=False,
            auto_seed=False,
            jwt_secret=None,
        )


def test_frontend_does_not_persist_tokens_or_prefill_demo_credentials():
    root = Path(__file__).resolve().parents[2]
    api_source = (root / "frontend/lib/api.ts").read_text()
    login_source = (root / "frontend/app/login/page.tsx").read_text()
    assert "localStorage" not in api_source
    assert "LocalDemoPass123!" not in login_source
    assert 'useState("")' in login_source


def test_public_registration_cannot_self_assign_privileged_role(client):
    response = client.post(
        "/auth/register",
        json={
            "email": "self-admin@example.com",
            "password": "DemoPassword123!",
            "role": "admin",
        },
    )

    assert response.status_code == 200, response.text
    assert response.json()["user"]["role"] == "viewer"
    token = response.json()["access_token"]
    audit_response = client.get("/admin/audit-logs", headers={"Authorization": f"Bearer {token}"})
    assert audit_response.status_code == 403


def test_reject_invalid_password(client):
    response = client.post(
        "/auth/login", json={"email": "engineer@example.com", "password": "wrong"}
    )
    assert response.status_code == 401


def test_token_required_for_protected_route(client):
    response = client.get("/incidents")
    assert response.status_code == 401


def test_viewer_cannot_run_tools(client, viewer_headers, incident_id):
    response = client.post(
        "/mcp/tools/search-logs",
        headers=viewer_headers,
        json={"incident_id": incident_id, "query": "timeout"},
    )
    assert response.status_code == 403


def test_admin_can_access_audit_logs(client, admin_headers):
    response = client.get("/admin/audit-logs", headers=admin_headers)
    assert response.status_code == 200


def test_non_admin_cannot_access_admin(client, engineer_headers):
    response = client.get("/admin/audit-logs", headers=engineer_headers)
    assert response.status_code == 403


def test_route_role_matrix_denies_privileged_operations(
    client, viewer_headers, engineer_headers, commander_headers
):
    assert client.post(
        "/alerts",
        headers=viewer_headers,
        json={
            "service_id": "missing",
            "alert_name": "blocked",
            "metric_name": "latency",
            "metric_value": 2,
            "threshold": 1,
        },
    ).status_code == 403
    assert client.get("/admin/security", headers=engineer_headers).status_code == 403
    assert client.get("/approvals", headers=commander_headers).status_code == 200
