from __future__ import annotations

import logging
from datetime import UTC, datetime

from app.db import get_supabase

logger = logging.getLogger(__name__)

# Ordered pipeline stages that may emit a provenance event. `summary` is a
# terminal run state, not an emitted event (see CLAUDE.md), so it is excluded.
EMITTABLE_STAGES = ("input", "fields", "extract", "simulate", "score", "results")


def list_provenance_events(run_id: str) -> list[dict]:
    client = get_supabase()
    response = (
        client.table("provenance_events")
        .select("*")
        .eq("run_id", run_id)
        .order("occurred_at")
        .execute()
    )
    return response.data


def emit(
    run_id: str,
    stage: str,
    event_type: str,
    message: str,
    payload: dict | None = None,
    duration_ms: int | None = None,
) -> dict | None:
    """Write a single provenance event for *run_id* and return the inserted row.

    `stage` must be one of EMITTABLE_STAGES — an unknown stage is a programming
    error and raises ValueError. A DB failure, by contrast, must never crash a
    run: provenance is an audit trail, so a failed write is logged and None is
    returned, leaving a gap in the trail rather than aborting live work.

    `occurred_at` is stamped here (not left to the DB default) so events emitted
    in rapid succession keep a stable, microsecond-resolution order.
    """
    if stage not in EMITTABLE_STAGES:
        raise ValueError(
            f"unknown provenance stage {stage!r}; expected one of {EMITTABLE_STAGES}"
        )

    event = {
        "run_id": run_id,
        "stage": stage,
        "event_type": event_type,
        "message": message,
        "payload": payload,
        "occurred_at": datetime.now(UTC).isoformat(),
        "duration_ms": duration_ms,
    }
    try:
        client = get_supabase()
        response = client.table("provenance_events").insert(event).execute()
        return (response.data or [None])[0]
    except Exception as exc:
        logger.warning(
            "provenance emit failed (run=%s stage=%s): %s", run_id, stage, exc
        )
        return None
