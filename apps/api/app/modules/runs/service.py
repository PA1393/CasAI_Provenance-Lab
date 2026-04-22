from datetime import UTC, datetime

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
    now = datetime.now(UTC).isoformat()
    payload = {
        "research_object_id": research_object_id,
        "prompt": prompt,
        "status": "running",
        "started_at": now,
    }
    response = client.table("runs").insert(payload).execute()
    return response.data[0]
