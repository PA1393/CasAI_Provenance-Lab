from fastapi.testclient import TestClient

from app.api.routes import runs as runs_routes
from app.main import app

client = TestClient(app)


def test_get_runs_returns_service_items(monkeypatch) -> None:
    monkeypatch.setattr(
        runs_routes,
        "list_runs",
        lambda: [
            {
                "run_id": f"run-{index}",
                "research_object_id": "ro-1",
                "created_at": "2026-01-01T00:00:00Z",
                "prompt": "test",
                "status": "completed",
                "started_at": "2026-01-01T00:00:00Z",
                "completed_at": "2026-01-01T00:00:01Z",
                "guide_rna": None,
                "current_stage": "summary",
            }
            for index in range(2)
        ],
    )

    response = client.get("/api/v1/runs")

    assert response.status_code == 200
    payload = response.json()
    assert "items" in payload
    assert len(payload["items"]) == 2
