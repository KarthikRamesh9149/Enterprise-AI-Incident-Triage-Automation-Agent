"""Regression tests locking the AI + security layers to REAL behavior.

Guards against: the password-hash leak via serialize(), the agent's constant
confidence_score of 0.86 + fixed hypothesis, and the tautological eval case.
"""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.services.seed import DEMO_PASSWORD

_OLD_FIXED_HYPOTHESIS = (
    "Recent payment gateway retry fanout likely amplified downstream timeout latency."
)


def _headers(client: TestClient, email: str, password: str = DEMO_PASSWORD) -> dict[str, str]:
    resp = client.post("/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def _first_incident_id(client: TestClient, headers: dict[str, str]) -> str:
    incidents = client.get("/incidents", headers=headers).json()
    assert incidents, "seed should provide at least one incident"
    return incidents[0]["id"]


def test_password_hash_is_never_serialized(client: TestClient):
    reg = client.post(
        "/auth/register",
        json={"email": "leak-check@example.com", "password": DEMO_PASSWORD},
    )
    assert reg.status_code in (200, 201), reg.text
    assert "hashed_password" not in str(reg.json())
    me = client.get("/auth/me", headers=_headers(client, "leak-check@example.com"))
    assert me.status_code == 200
    assert "hashed_password" not in me.json()


def test_agent_confidence_is_signal_derived_not_constant(client: TestClient):
    commander = _headers(client, "commander@example.com")
    incident_id = _first_incident_id(client, commander)
    resp = client.post(
        "/agent/run-incident-triage", headers=commander, json={"incident_id": incident_id}
    )
    assert resp.status_code == 200, resp.text
    run = resp.json()["agent_run"]
    # Not the old hardcoded constant, and within the derived clamp range.
    assert run["confidence_score"] != 0.86
    assert 0.05 <= run["confidence_score"] <= 0.95
    # The hypothesis is derived from evidence, not the old fixed string.
    assert resp.json()["hypothesis"]["hypothesis"] != _OLD_FIXED_HYPOTHESIS
    trace = client.get(f"/agent/runs/{run['id']}/trace", headers=commander).json()
    assert any(step["node_name"] == "confidence_estimate" for step in trace)


def test_eval_is_real_with_negative_controls(client: TestClient):
    admin = _headers(client, "admin@example.com")
    run = client.post("/evals/run", headers=admin, json={})
    assert run.status_code == 200, run.text
    assert run.json()["metrics_json"]["pass_rate"] == 1
    assert run.json()["metrics_json"]["cases"] >= 5

    run_id = run.json()["id"]
    cases = client.get(f"/evals/runs/{run_id}/cases", headers=admin).json()
    by_type = {c["incident_type"]: c for c in cases}
    # Negative controls exist and expect False — an always-True impl fails these.
    neg_redact = by_type["redaction_negative_control"]["expected_outputs_json"]
    neg_inject = by_type["prompt_injection_negative_control"]["expected_outputs_json"]
    assert neg_redact == {"redacted": False}
    assert neg_inject == {"blocked": False}
    # The RBAC gate case is computed from the real role policy.
    assert by_type["rbac_privileged_action_gate"]["passed"] is True
