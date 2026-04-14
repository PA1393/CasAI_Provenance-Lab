from datetime import UTC, datetime


def list_runs() -> list[dict]:
    now = datetime.now(UTC).isoformat()

    return [
        {
            "run_id": "run_001",
            "research_object_id": "ro_001",
            "status": "draft",
            "mode": "base-editing",
            "created_at": now,
        },
        {
            "run_id": "run_002",
            "research_object_id": "ro_002",
            "status": "ready",
            "mode": "crispr-compare",
            "created_at": now,
        },
    ]
