def test_seed_data_exists(client, engineer_headers):
    assert client.get("/services", headers=engineer_headers).json()
    assert client.get("/incidents", headers=engineer_headers).json()
    assert client.get("/runbooks", headers=engineer_headers).json()


def test_search_logs_redacts_secrets(client, engineer_headers, incident_id):
    response = client.post(
        "/mcp/tools/search-logs",
        headers=engineer_headers,
        json={"incident_id": incident_id, "query": "timeout"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["count"] >= 1
    assert "[REDACTED]" in str(body)
    assert "sk_live_not_real" not in str(body)


def test_search_runbooks_flags_prompt_injection(client, engineer_headers, incident_id):
    incident = client.get(f"/incidents/{incident_id}", headers=engineer_headers).json()
    response = client.post(
        "/mcp/tools/search-runbooks",
        headers=engineer_headers,
        json={"service_id": incident["service_id"], "query": "suspicious"},
    )
    assert response.status_code == 200
    runbooks = response.json()["runbooks"]
    assert any(row["injection_warning"] for row in runbooks)


def test_commander_can_create_draft_and_approval(client, commander_headers, incident_id):
    response = client.post(
        "/mcp/tools/create-ticket-draft",
        headers=commander_headers,
        json={"incident_id": incident_id},
    )
    assert response.status_code == 200
    assert response.json()["approval"]["status"] == "pending"


def test_incident_agent_runs_and_persists_trace(client, commander_headers, incident_id):
    response = client.post(
        "/agent/run-incident-triage",
        headers=commander_headers,
        json={"incident_id": incident_id},
    )
    assert response.status_code == 200
    run_id = response.json()["agent_run"]["id"]
    trace = client.get(f"/agent/runs/{run_id}/trace", headers=commander_headers)
    assert trace.status_code == 200
    assert len(trace.json()) >= 8


def test_approval_gate_and_mock_action(client, commander_headers, incident_id):
    draft = client.post(
        "/mcp/tools/draft-status-update",
        headers=commander_headers,
        json={"incident_id": incident_id},
    ).json()
    approval_id = draft["approval"]["id"]
    approved = client.post(
        f"/approvals/{approval_id}/approve",
        headers=commander_headers,
        json={"reviewer_notes": "safe local demo"},
    )
    assert approved.status_code == 200
    action = client.post(
        "/actions/mock-send-status-update",
        headers=commander_headers,
        json={"incident_id": incident_id},
    )
    assert action.status_code == 200
    assert action.json()["status"] == "executed"


def test_report_and_evals(client, admin_headers, incident_id):
    report = client.post(
        "/reports/generate", headers=admin_headers, json={"incident_id": incident_id}
    )
    assert report.status_code == 200
    assert "[REDACTED]" in report.json()["markdown_content"]
    eval_run = client.post("/evals/run", headers=admin_headers, json={})
    assert eval_run.status_code == 200
    assert eval_run.json()["metrics_json"]["pass_rate"] == 1
