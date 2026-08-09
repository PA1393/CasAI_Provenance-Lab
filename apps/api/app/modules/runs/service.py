from __future__ import annotations

import logging
import time
from datetime import UTC, datetime

from app.db import get_supabase
from app.modules.provenance.service import emit
from app.modules.simulation.engine import apply_base_edit
from app.modules.simulation.scoring import off_target_score, on_target_score
from app.modules.simulation.spec import EditSpec, resolve_edit_spec, validate_edit_spec

logger = logging.getLogger(__name__)

# Base each editor converts, for a human-readable edit summary.
_EDIT_CHANGE = {"CBE": ("C", "T"), "ABE": ("A", "G")}


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


def list_runs_by_research_object(research_object_id: str) -> list[dict]:
    client = get_supabase()
    response = (
        client.table("runs")
        .select("*")
        .eq("research_object_id", research_object_id)
        .order("created_at", desc=True)
        .execute()
    )
    return response.data


class _PipelineHalt(Exception):
    """Raised to stop the pipeline after a failure event has been emitted.

    Carries the stage that failed so create_run() can record it on the run.
    """

    def __init__(self, stage: str) -> None:
        self.stage = stage
        super().__init__(stage)


def create_run(research_object_id: str, prompt: str) -> dict:
    """Execute the real base-edit pipeline for a research object + prompt.

    Runs the analysis agent -> validation gate -> engine -> scoring chain,
    emitting a provenance event per stage with real timing, then writes the
    real result. A stage failure (no sequence, unresolved intent, invalid
    spec) emits a failure event and marks the run `failed` rather than raising.
    """
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

    run = (
        client.table("runs")
        .insert(
            {
                "research_object_id": research_object_id,
                "prompt": prompt,
                "status": "running",
                "current_stage": "input",
                "started_at": now.isoformat(),
            }
        )
        .execute()
        .data[0]
    )
    run_id = run["run_id"]

    try:
        _run_pipeline(client, run_id, ro, prompt)
    except _PipelineHalt as halt:
        _finish(client, run_id, status="failed", stage=halt.stage)
    except Exception:
        # Anything that isn't a handled _PipelineHalt is unexpected (LLM/network
        # hiccup, a DB write failure mid-pipeline, ...). The run must not be left
        # stuck at status="running" forever with no completed_at just because the
        # failure wasn't one we anticipated — best-effort mark it failed at
        # whatever stage it reached, then re-raise so the caller still sees a
        # real error instead of a silently "successful" response.
        #
        # The cleanup is itself best-effort: if the DB is what failed, these
        # writes fail too. Swallow that secondary error and log it so the bare
        # `raise` below always propagates the ORIGINAL root cause, not a masking
        # DB error from the cleanup path.
        try:
            stalled = (
                client.table("runs")
                .select("current_stage")
                .eq("run_id", run_id)
                .maybe_single()
                .execute()
            )
            stage = (stalled.data or {}).get("current_stage") or "input"
            _finish(client, run_id, status="failed", stage=stage)
        except Exception as cleanup_exc:
            logger.warning(
                "failed to mark run %s failed after an unexpected error: %s",
                run_id,
                cleanup_exc,
            )
        raise
    else:
        _finish(client, run_id, status="completed", stage="summary")

    updated = (
        client.table("runs").select("*").eq("run_id", run_id).maybe_single().execute()
    )
    return updated.data


def _run_pipeline(client, run_id: str, ro: dict, prompt: str) -> None:
    # ── input ──────────────────────────────────────────────────────────────
    _advance(client, run_id, "input")
    sequence = (ro.get("sequence") or "").upper()
    if not sequence:
        _halt(
            run_id,
            "input",
            "input_invalid",
            "No sequence on the research object — cannot run the base-edit pipeline",
            payload={"research_object_id": ro.get("research_object_id")},
        )
    emit(
        run_id,
        "input",
        "input_validated",
        "Sequence loaded from research object",
        payload={
            "research_object_id": ro.get("research_object_id"),
            "sequence_length": len(sequence),
        },
    )

    # ── extract: analysis agent + validation gate ──────────────────────────
    _advance(client, run_id, "extract")
    started = time.perf_counter()
    try:
        spec = resolve_edit_spec(prompt, sequence)
    except Exception as exc:
        # Broad on purpose: resolve_edit_spec raises ValueError for a missing key,
        # bad JSON, or no guide site — but an OpenAI network/rate-limit error is a
        # different exception type entirely. Either way it belongs to "extract",
        # so it's classified here rather than falling through to a generic
        # unhandled-error path with no stage context.
        _halt(
            run_id,
            "extract",
            "analysis_failed",
            f"Analysis agent could not resolve an edit spec: {exc}",
            duration_ms=_ms(started),
        )
    emit(
        run_id,
        "extract",
        "intent_resolved",
        "Analysis agent resolved a candidate edit spec",
        payload=_spec_payload(spec),
        duration_ms=_ms(started),
    )

    problems = validate_edit_spec(spec, sequence)
    if problems:
        _halt(
            run_id,
            "extract",
            "schema_invalid",
            "EditSpec failed the validation gate",
            payload={"problems": problems, "spec": _spec_payload(spec)},
        )
    emit(
        run_id,
        "extract",
        "schema_validated",
        "EditSpec passed the validation gate",
        payload={"problems": []},
    )

    # ── simulate: deterministic base-edit engine ───────────────────────────
    _advance(client, run_id, "simulate")
    started = time.perf_counter()
    edit = apply_base_edit(
        sequence, spec.guide_rna, spec.edit_type, window=spec.window, pam=spec.pam
    )
    emit(
        run_id,
        "simulate",
        "simulation_executed",
        "Base-edit engine applied the spec to the sequence",
        payload={
            "edited": edit["edited"],
            "strand": edit["strand"],
            "protospacer_start": edit["protospacer_start"],
            "edited_positions": edit["edited_positions"],
            "pam_found": edit["pam_found"],
            "reason": edit["reason"],
        },
        duration_ms=_ms(started),
    )

    # ── score: on-target efficiency + off-target risk ──────────────────────
    _advance(client, run_id, "score")
    started = time.perf_counter()
    on_t = on_target_score(spec.guide_rna)
    off_t = off_target_score(sequence, spec.guide_rna)
    emit(
        run_id,
        "score",
        "edit_scored",
        "Guide scored for on-target efficiency and off-target risk",
        payload={"on_target_score": on_t, "off_target_score": off_t},
        duration_ms=_ms(started),
    )

    # ── results: persist the real outcome ──────────────────────────────────
    _advance(client, run_id, "results")
    client.table("results").insert(
        {
            "run_id": run_id,
            "research_object_id": ro.get("research_object_id"),
            "edited_sequence": edit["edited_sequence"],
            "edit_summary": _summarize(spec, edit),
            "on_target_score": on_t,
            "off_target_score": off_t,
            "reproducible": True,
            "notes": spec.rationale,
        }
    ).execute()
    emit(
        run_id,
        "results",
        "results_packaged",
        "Results and provenance package prepared",
        payload={"run_id": run_id, "edited_positions": edit["edited_positions"]},
    )


def _halt(
    run_id: str,
    stage: str,
    event_type: str,
    message: str,
    payload: dict | None = None,
    duration_ms: int | None = None,
) -> None:
    """Emit a failure event for *stage*, then stop the pipeline."""
    emit(run_id, stage, event_type, message, payload=payload, duration_ms=duration_ms)
    raise _PipelineHalt(stage)


def _advance(client, run_id: str, stage: str) -> None:
    """Move the run's current_stage marker so the UI tracks live progress."""
    client.table("runs").update({"current_stage": stage}).eq("run_id", run_id).execute()


def _finish(client, run_id: str, status: str, stage: str) -> None:
    client.table("runs").update(
        {
            "status": status,
            "current_stage": stage,
            "completed_at": datetime.now(UTC).isoformat(),
        }
    ).eq("run_id", run_id).execute()


def _ms(started: float) -> int:
    return int((time.perf_counter() - started) * 1000)


def _spec_payload(spec: EditSpec) -> dict:
    return {
        "edit_type": spec.edit_type,
        "guide_rna": spec.guide_rna,
        "strand": spec.strand,
        "organism": spec.organism,
        "gene": spec.gene,
        "rationale": spec.rationale,
    }


def _summarize(spec: EditSpec, edit: dict) -> str:
    if not edit["edited"]:
        return f"No edit applied ({edit['reason']})."
    frm, to = _EDIT_CHANGE[spec.edit_type]
    positions = ", ".join(str(p) for p in edit["edited_positions"])
    return (
        f"{spec.edit_type} {frm}->{to} on {edit['strand']} strand at "
        f"position(s) {positions} (guide {spec.guide_rna})."
    )
