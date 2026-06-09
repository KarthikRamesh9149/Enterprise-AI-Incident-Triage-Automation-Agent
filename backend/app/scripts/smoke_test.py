from fastapi.testclient import TestClient

from app.main import app

if __name__ == "__main__":
    client = TestClient(app)
    health = client.get("/health")
    print(health.json())
    assert health.status_code == 200
