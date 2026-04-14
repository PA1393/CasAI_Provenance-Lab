from datetime import UTC, datetime


def list_provenance_events(run_id: str) -> list[dict]:
    now = datetime.now(UTC).isoformat()

    return [
        {
            "event_id": "evt_001",
            "run_id": run_id,
            "event_type": "run.created",
            "timestamp": now,
            "sequence": 1,
        },
        {
            "event_id": "evt_002",
            "run_id": run_id,
            "event_type": "run.started",
            "timestamp": now,
            "sequence": 2,
        },
    ]
