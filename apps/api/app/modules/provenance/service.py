from app.db import get_supabase


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
