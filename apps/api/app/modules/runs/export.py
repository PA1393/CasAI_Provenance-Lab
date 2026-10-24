"""Portable, deterministic demo snapshots. Not a rights clearance or full archive."""

import hashlib
import json

from app.modules.provenance.service import list_provenance_events
from app.modules.research_objects.service import get_research_object
from app.modules.results.service import list_results
from app.modules.runs.service import get_run
from app.schemas.provenance import ProvenanceEvent
from app.schemas.research_objects import ResearchObject
from app.schemas.results import Result
from app.schemas.runs import Run

MAX_EXPORT_BYTES = 24_000_000


def canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                      allow_nan=False)


def build_run_export(run_id: str) -> dict | None:
    raw = get_run(run_id)
    if raw is None:
        return None
    run = Run.model_validate(raw)
    if run.status not in {"completed", "failed"}:
        raise ValueError("Wait for a terminal run before exporting a snapshot")
    research = get_research_object(run.research_object_id)
    if research is None:
        raise ValueError("The run input is unavailable; an incomplete export was not created")
    # Explicit schemas prevent accidentally exporting future DB-only credentials/columns.
    documents = {
        "run.json": run.model_dump(mode="json"),
        "input.json": ResearchObject.model_validate(research).model_dump(mode="json"),
        "results.json": sorted(
            [Result.model_validate(row).model_dump(mode="json") for row in list_results(run_id)],
            key=lambda row: row["result_id"],
        ),
        "provenance.json": sorted(
            [ProvenanceEvent.model_validate(row).model_dump(mode="json")
             for row in list_provenance_events(run_id)],
            key=lambda row: (row["occurred_at"], row["event_id"]),
        ),
    }
    files = []
    for path, value in documents.items():
        content = canonical_json(value)
        encoded = content.encode("utf-8")
        files.append({"path": path, "content": content, "encoding": "utf-8",
                      "byte_length": len(encoded),
                      "sha256": hashlib.sha256(encoded).hexdigest()})
    package = {
        "schema_version": "casai.demo-export.v1", "run_id": run_id, "files": files,
        "rights": {"status": "unverified", "commercial_reuse_authorized": False},
        "limitations": [
            "Snapshot of currently recorded demo data, not an immutable scientific archive.",
            "Raw uploads, approved mappings/plans, trajectories and PDF are not included.",
            "Heuristic scores and illustrative scenes are not experimental validation.",
            "Rights are unverified; this grants no license or commercial permission.",
            "Historical data may contain placeholders; checksums establish byte integrity only.",
        ],
    }
    if len(canonical_json(package).encode("utf-8")) > MAX_EXPORT_BYTES:
        raise ValueError("Export exceeds the demo size limit; no truncated package was created")
    return package
