# Research objects service — all DB access for this domain lives here.
# Mock field generation is isolated to _build_mock_fields(); nothing else generates fake data.

from __future__ import annotations

import hashlib

from app.db import get_supabase
from app.modules.research_objects.fasta import parse_fasta


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


def _fields_from_fasta(fasta_text: str) -> dict:
    """Parse uploaded FASTA into the real fields it determines.

    Alongside the parsed sequence this derives a content-addressed `ro_hash`, so
    two identical uploads hash identically — the reproducibility claim the
    provenance trail makes is only meaningful if the hash tracks real content.

    Raises ValueError (from parse_fasta) if the FASTA is malformed.
    """
    parsed = parse_fasta(fasta_text)
    digest = hashlib.sha256(parsed["sequence"].encode()).hexdigest()
    return {**parsed, "ro_hash": f"sha256:{digest}"}


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
    """Create a research object, parsing `fasta_text` when the caller supplies one.

    `fasta_text` is upload input rather than a column: it is consumed here and
    replaced by the fields it determines (sequence, sequence_length, gc_content,
    fasta_preview, ro_hash), which take precedence over the placeholders. Fields
    a FASTA cannot determine — structure refs, QC read counts — stay mocked until
    those pipelines exist.

    Without `fasta_text` no sequence is stored, and the base-edit pipeline will
    halt at `input` for this research object rather than invent one.

    Raises ValueError if `fasta_text` is present but malformed.
    """
    payload = {k: v for k, v in data.items() if k != "fasta_text"}
    payload.update(_build_mock_fields(data["pdb_id"]))

    fasta_text = data.get("fasta_text")
    if fasta_text:
        payload.update(_fields_from_fasta(fasta_text))

    client = get_supabase()
    response = client.table("research_objects").insert(payload).execute()
    return response.data[0]
