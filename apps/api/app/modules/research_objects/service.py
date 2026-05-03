# Research objects service — all DB access for this domain lives here.
# Mock field generation is isolated to _build_mock_fields(); nothing else generates fake data.

from app.db import get_supabase


def _build_mock_fields(pdb_id: str) -> dict:
    """Generate placeholder computed fields until real parsing/fetch is implemented."""
    return {
        "mmcif_fetched_from": f"https://files.rcsb.org/download/{pdb_id}.cif",
        "mmcif_hash": "mock:mmcif_hash_placeholder",
        "sequence_length": 1500,
        "gc_content": 0.52,
        "avg_phred_score": 35.0,
        "reads_passing_qc": 980000,
        "reads_total": 1000000,
        "ro_hash": f"sha256:mock_ro_hash_{pdb_id.lower()}",
        "status": "ready",
        "fasta_preview": "ATGCGATCGGTACTAGTACGATCGGTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGC...",
        "target_region": [720, 742],
    }


def list_research_objects() -> list[dict]:
    client = get_supabase()
    response = client.table("research_objects").select("*").execute()
    return response.data


def get_research_object(research_object_id: str) -> dict | None:
    client = get_supabase()
    response = (
        client.table("research_objects")
        .select("*")
        .eq("research_object_id", research_object_id)
        .maybe_single()
        .execute()
    )
    return response.data


def create_research_object(data: dict) -> dict:
    client = get_supabase()
    payload = {**data, **_build_mock_fields(data["pdb_id"])}
    response = client.table("research_objects").insert(payload).execute()
    return response.data[0]
