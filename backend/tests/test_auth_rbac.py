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
