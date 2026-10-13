from fastapi.testclient import TestClient

from app.api.routes import runs as routes
from app.main import app

client = TestClient(app)


def test_get_runs_returns_service_items_without_live_supabase(monkeypatch) -> None:
    items = [
        {
            "run_id": f"run-{index}",
            "research_object_id": "ro-1",
            "created_at": "2026-01-01T00:00:00Z",
            "prompt": "synthetic CBE demonstration",
            "status": "queued",
            "started_at": None,
            "completed_at": None,
        }
        for index in (1, 2)
    ]
    monkeypatch.setattr(routes, "list_runs", lambda: items)
    response = client.get("/api/v1/runs")

    assert response.status_code == 200
    payload = response.json()
    assert "items" in payload
    assert len(payload["items"]) == 2
    assert [item["run_id"] for item in payload["items"]] == ["run-1", "run-2"]


def test_get_runs_returns_an_empty_list(monkeypatch) -> None:
    monkeypatch.setattr(routes, "list_runs", lambda: [])
    response = client.get("/api/v1/runs")
    assert response.status_code == 200
    assert response.json() == {"items": []}
