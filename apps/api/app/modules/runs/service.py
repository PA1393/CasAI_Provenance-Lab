from datetime import UTC, datetime, timedelta

from app.db import get_supabase


def list_runs() -> list[dict]:
    client = get_supabase()
    response = client.table("runs").select("*").order("created_at", desc=True).execute()
    return response.data


def get_run(run_id: str) -> dict | None:
    client = get_supabase()
    response = (
        client.table("runs")
        .select("*")
        .eq("run_id", run_id)
        .maybe_single()
        .execute()
    )
    return response.data


def create_run(research_object_id: str, prompt: str) -> dict:
    client = get_supabase()
    now = datetime.now(UTC)

    ro_response = (
        client.table("research_objects")
        .select("*")
        .eq("research_object_id", research_object_id)
        .maybe_single()
        .execute()
    )
    ro = ro_response.data or {}

    run_payload = {
        "research_object_id": research_object_id,
        "prompt": prompt,
        "status": "running",
        "current_stage": "preflight",
        "started_at": now.isoformat(),
    }
    run_response = client.table("runs").insert(run_payload).execute()
    run = run_response.data[0]
    run_id = run["run_id"]

    events = _build_mock_provenance_events(run_id, ro, prompt, base_time=now)
    client.table("provenance_events").insert(events).execute()

    result = _build_mock_result(run_id, ro)
    client.table("results").insert(result).execute()

    completed_at = (now + timedelta(seconds=6)).isoformat()
    client.table("runs").update({"status": "completed","current_stage": "summary" ,"completed_at": completed_at}).eq(
        "run_id", run_id
    ).execute()

    updated = (
        client.table("runs").select("*").eq("run_id", run_id).maybe_single().execute()
    )
    return updated.data


def _build_mock_provenance_events(
    run_id: str, ro: dict, prompt: str, base_time: datetime
) -> list[dict]:
    pdb_id = ro.get("pdb_id", "UNKNOWN")
    stages = [
        (
            "input_validated",
            "Input bundle validated successfully",
            {
                "research_object_id": ro.get("research_object_id"),
                "pdb_id": pdb_id,
                "reads_total": ro.get("reads_total", 0),
                "reads_passing_qc": ro.get("reads_passing_qc", 0),
                "avg_phred_score": ro.get("avg_phred_score", 0.0),
            },
        ),
        (
            "fields_extracted",
            "Core sequence and structural fields extracted",
            {
                "sequence_length": ro.get("sequence_length", 0),
                "gc_content": ro.get("gc_content", 0.0),
                "mmcif_fetched_from": ro.get("mmcif_fetched_from"),
                "mmcif_hash": ro.get("mmcif_hash"),
            },
        ),
        (
            "research_object_loaded",
            "Research Object loaded for simulation",
            {
                "research_object_id": ro.get("research_object_id"),
                "ro_hash": ro.get("ro_hash"),
                "status": ro.get("status", "ready"),
            },
        ),
        (
            "simulation_executed",
            "Instruction-driven simulation executed against sequence and structure context",
            {
                "prompt": prompt,
                "pdb_id": pdb_id,
                "sequence_length": ro.get("sequence_length", 0),
                "confidence": 0.87,
                "off_target_score": 0.05,
            },
        ),
        (
            "results_packaged",
            "Results and provenance package prepared",
            {
                "run_id": run_id,
                "result_count": 1,
                "provenance_event_count": 5,
            },
        ),
    ]
    return [
        {
            "run_id": run_id,
            "event_type": event_type,
            "message": message,
            "payload": payload,
            "occurred_at": (base_time + timedelta(seconds=i + 1)).isoformat(),
            "stage": event_type.split("_")[0],  # crude stage assignment
            "duration_ms": 1000 + i * 500,  # mock durations
        }
        for i, (event_type, message, payload) in enumerate(stages)
    ]


def _build_mock_result(run_id: str, ro: dict) -> dict:
    pdb_id = ro.get("pdb_id", "UNKNOWN")
    reads_passing = ro.get("reads_passing_qc", 0)
    reads_total = ro.get("reads_total", 0)
    return {
        "run_id": run_id,
        "research_object_id": ro.get("research_object_id"),
        "edited_sequence": f"ATGCGATCGGTA...{pdb_id[:4]}...CTAGTACG",
        "edit_summary": (
            f"Base edit at position 742 (A→G) targeting {pdb_id} structural context. "
            "Edit efficiency estimated at 87%. Off-target probability low."
        ),
        "off_target_score": 0.05,
        "on_target_score": 0.82,
        "off_target_score": 0.14,
        "reproducible": True,
        "notes": (
            f"Simulated outcome using {pdb_id} mmCIF context. "
            f"QC passed ({reads_passing}/{reads_total} reads)."
        ),
    }
