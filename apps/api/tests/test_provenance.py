import pytest

from app.modules.provenance import service
from app.schemas.provenance import ProvenanceEvent


@pytest.mark.parametrize("event_type,expected", [
    ("input_received", "pending"), ("input_validated", "completed"),
    ("intent_resolved", "running"), ("schema_validated", "completed"),
    ("input_invalid", "failed"), ("analysis_failed", "failed"),
    ("schema_invalid", "failed"), ("simulation_executed", "completed"),
    ("edit_scored", "completed"), ("results_packaged", "completed"),
    ("scientific_tool_failed", "failed"), ("scientific_tool_completed", "completed"),
    ("unrecognized_validated", "unknown"),
])
def test_provenance_api_provides_explicit_stage_status(monkeypatch, event_type, expected):
    from fastapi.testclient import TestClient

    from app.api.routes import provenance as routes
    from app.main import app

    row = dict(event_id="event", run_id="run", stage="extract", event_type=event_type,
               message="synthetic", occurred_at="2026-10-22T00:00:00Z")
    monkeypatch.setattr(routes, "list_provenance_events", lambda run_id: [row])
    response = TestClient(app).get("/api/v1/runs/run/provenance")
    assert response.status_code == 200
    assert response.json()["items"][0]["stage_status"] == expected
    assert ProvenanceEvent(**row).model_dump()["stage_status"] == expected


class _Recorder:
    """Minimal Supabase stub that records a single provenance insert."""

    def __init__(self) -> None:
        self.inserted: dict | None = None

    def table(self, name: str):
        assert name == "provenance_events"
        return self

    def insert(self, row: dict):
        self.inserted = row
        return self

    def execute(self):
        return type("Resp", (), {"data": [self.inserted]})()


def test_emit_writes_a_row(monkeypatch) -> None:
    rec = _Recorder()
    monkeypatch.setattr(service, "get_supabase", lambda: rec)

    row = service.emit(
        "run-1", "simulate", "simulation_executed", "ran", payload={"k": "v"}, duration_ms=42
    )

    assert rec.inserted["run_id"] == "run-1"
    assert rec.inserted["stage"] == "simulate"
    assert rec.inserted["event_type"] == "simulation_executed"
    assert rec.inserted["payload"] == {"k": "v"}
    assert rec.inserted["duration_ms"] == 42
    assert "occurred_at" in rec.inserted  # stamped here, not left to the DB default
    assert row["run_id"] == "run-1"


def test_emit_rejects_unknown_stage(monkeypatch) -> None:
    # A bad stage is a programming error, not a runtime hiccup — it must raise
    # (and never reach the DB).
    monkeypatch.setattr(service, "get_supabase", lambda: pytest.fail("should not touch DB"))
    with pytest.raises(ValueError):
        service.emit("run-1", "summary", "x", "y")  # summary is terminal, not emittable


def test_emit_does_not_crash_on_db_failure(monkeypatch) -> None:
    def boom():
        raise RuntimeError("db down")

    monkeypatch.setattr(service, "get_supabase", boom)
    # A failed provenance write must never crash a live run — logged, returns None.
    assert service.emit("run-1", "score", "edit_scored", "msg") is None
