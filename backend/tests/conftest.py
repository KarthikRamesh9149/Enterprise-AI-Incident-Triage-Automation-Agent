import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

os.environ["DATABASE_URL"] = "sqlite:///./test_incident_triage.sqlite3"
os.environ["AUTO_SEED"] = "true"
os.environ["LLM_PROVIDER"] = "mock"
os.environ["JWT_SECRET"] = "test-secret-change-me-12345-32-bytes-minimum"

from app.db.session import init_db  # noqa: E402
from app.main import app  # noqa: E402
from app.services.seed import DEMO_PASSWORD  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def clean_db():
    path = Path("test_incident_triage.sqlite3")
    if path.exists():
        path.unlink()
    init_db()
    yield
    if path.exists():
        try:
            path.unlink()
        except PermissionError:
            pass


@pytest.fixture()
def client():
    with TestClient(app) as test_client:
        yield test_client


def token(client: TestClient, email: str) -> str:
    response = client.post("/auth/login", json={"email": email, "password": DEMO_PASSWORD})
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


@pytest.fixture()
def admin_headers(client):
    return {"Authorization": f"Bearer {token(client, 'admin@example.com')}"}


@pytest.fixture()
def commander_headers(client):
    return {"Authorization": f"Bearer {token(client, 'commander@example.com')}"}


@pytest.fixture()
def engineer_headers(client):
    return {"Authorization": f"Bearer {token(client, 'engineer@example.com')}"}


@pytest.fixture()
def viewer_headers(client):
    return {"Authorization": f"Bearer {token(client, 'viewer@example.com')}"}


@pytest.fixture()
def incident_id(client, engineer_headers):
    rows = client.get("/incidents", headers=engineer_headers).json()
    for row in rows:
        if row["title"] == "Checkout API payment timeout spike":
            return row["id"]
    raise AssertionError("Demo checkout incident not found")
