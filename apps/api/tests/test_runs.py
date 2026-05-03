from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_get_runs_returns_placeholder_items() -> None:
    response = client.get("/api/v1/runs")

    assert response.status_code == 200
    payload = response.json()
    assert "items" in payload
    assert len(payload["items"]) == 2
