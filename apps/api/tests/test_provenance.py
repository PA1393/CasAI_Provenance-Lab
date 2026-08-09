import pytest

from app.modules.provenance import service


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
