# Research objects service — all DB access for this domain lives here.
# Unavailable measurements remain null until a real adapter provides them.

from __future__ import annotations

import hashlib
import json

from app.db import get_supabase
from app.modules.research_objects.fasta import parse_fasta


def _unmeasured_fields(data: dict) -> dict:
    """Keep unavailable measurements explicit instead of generating placeholders."""
    identity = json.dumps(data, sort_keys=True, separators=(",", ":")).encode()
    return {
        "mmcif_fetched_from": None,
        "mmcif_hash": None,
        "sequence_length": None,
        "gc_content": None,
        "avg_phred_score": None,
        "reads_passing_qc": None,
        "reads_total": None,
        "ro_hash": f"sha256:{hashlib.sha256(identity).hexdigest()}",
        "status": "draft",
        "fasta_preview": None,
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
    fasta_preview, ro_hash). Unmeasured structure and read-QC fields remain null.
    Supplied target coordinates are retained and validated as 1-based inclusive.

    Without `fasta_text` no sequence is stored, and the base-edit pipeline will
    halt at `input` for this research object rather than invent one.

    Raises ValueError if `fasta_text` is present but malformed.
    """
    payload = {k: v for k, v in data.items() if k != "fasta_text"}
    payload.update(_unmeasured_fields(payload))

    fasta_text = data.get("fasta_text")
    if fasta_text is not None:
        payload.update(_fields_from_fasta(fasta_text))
        payload["status"] = "ready"

    region = payload.get("target_region")
    if region is not None:
        if (
            len(region) != 2
            or any(type(value) is not int for value in region)
            or region[0] < 1
            or region[1] < region[0]
        ):
            raise ValueError("Target region must be two 1-based inclusive integers")
        length = payload.get("sequence_length")
        if length is not None and region[1] > length:
            raise ValueError("Target region extends beyond the supplied sequence")

    client = get_supabase()
    response = client.table("research_objects").insert(payload).execute()
    return response.data[0]
