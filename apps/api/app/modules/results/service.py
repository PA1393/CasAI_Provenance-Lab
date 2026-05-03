from app.db import get_supabase


def list_results(run_id: str) -> list[dict]:
    client = get_supabase()
    response = (
        client.table("results")
        .select("*")
        .eq("run_id", run_id)
        .execute()
    )
    return response.data
