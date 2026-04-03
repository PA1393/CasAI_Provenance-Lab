from datetime import UTC, datetime


def list_runs() -> list[dict[str, str]]:
    now = datetime.now(UTC).isoformat()

    return [
        {
            "id": "run_001",
            "name": "Base edit screen alpha",
            "status": "draft",
            "pipeline": "base-editing-v1",
            "createdAt": now,
        },
        {
            "id": "run_002",
            "name": "CRISPR comparison beta",
            "status": "ready",
            "pipeline": "crispr-compare-v1",
            "createdAt": now,
        },
    ]

