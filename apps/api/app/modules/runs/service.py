from __future__ import annotations

import logging
import time
from datetime import UTC, datetime

from app.api.dependencies import get_intake_workspace
from app.db import get_supabase
from app.modules.information_processor.handoff import validate_run_source
from app.modules.information_processor.workspace import WorkspaceError
from app.modules.provenance.service import emit
from app.modules.rag.service import VaultSearchError
from app.modules.runs.issues import RunIssue, run_issue
from app.modules.simulation.engine import apply_base_edit
from app.modules.simulation.scoring import off_target_score, on_target_score
from app.modules.simulation.spec import (
    AnalysisIssue,
    EditSpec,
    design_guide,
    resolve_edit_spec,
    validate_edit_spec,
)

logger = logging.getLogger(__name__)

# Base each editor converts, for a human-readable edit summary.
_EDIT_CHANGE = {"CBE": ("C", "T"), "ABE": ("A", "G")}
MAX_RUN_BASES = 5_000


class RunInputError(ValueError):
    """A bounded demo run cannot be prepared from this request."""


class RunInputNotFoundError(ValueError):
    """No research object exists for this run request."""


class ConfirmedSourceError(ValueError):
    """A linked confirmed input cannot be verified before a run is submitted."""


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

    def __init__(self, stage: str, issue: RunIssue) -> None:
        self.stage = stage
        self.issue = issue
        super().__init__(stage)


def create_run(research_object_id: str, prompt: str, execution_mode: str = "assisted") -> dict:
    """Execute the real base-edit pipeline for a research object + prompt.

    Runs the analysis agent -> validation gate -> engine -> scoring chain,
    emitting a provenance event per stage with real timing, then writes the
    real result. A stage failure (no sequence, unresolved intent, invalid
    spec) emits a failure event and marks the run `failed` rather than raising.
    """
    if execution_mode not in {"assisted", "demo_cbe", "demo_abe"}:
        raise RunInputError("Choose a supported execution mode")
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
    if not ro:
        raise RunInputNotFoundError("Research input not found")
    sequence = (ro.get("sequence") or "").upper()
    if len(sequence) > MAX_RUN_BASES:
        raise RunInputError("Demo runs accept at most 5,000 bases; prepare a smaller input")
    if execution_mode != "assisted" and (not sequence or set(sequence) - set("ACGT")):
        raise RunInputError("Rule-based demo runs require unambiguous A/C/G/T DNA")

    if ro.get("confirmed_version_id") or ro.get("confirmed_record_id"):
        try:
            validate_run_source(ro, get_intake_workspace())
        except (ValueError, WorkspaceError) as exc:
            raise ConfirmedSourceError(
                "Confirmed source is unavailable or changed; no run was submitted"
            ) from exc

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
        _run_pipeline(client, run_id, ro, prompt, execution_mode)
    except _PipelineHalt as halt:
        _finish(client, run_id, status="failed", stage=halt.stage, failure=halt.issue)
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
            issue = run_issue(stage, "unexpected_error")
            emit(run_id, stage, "stage_failed", issue.message,
                 payload={"failure": issue.model_dump()})
            _finish(client, run_id, status="failed", stage=stage, failure=issue)
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


def _run_pipeline(
    client, run_id: str, ro: dict, prompt: str, execution_mode: str = "assisted",
) -> None:
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
            "execution_mode": execution_mode,
            "target_region_policy": "metadata_only_full_sequence",
            "target_region_annotation": ro.get("target_region"),
            **({"confirmed_version_id": ro["confirmed_version_id"],
                "confirmed_record_id": ro["confirmed_record_id"]}
               if ro.get("confirmed_version_id") else {}),
        },
    )

    # ── extract: analysis agent + validation gate ──────────────────────────
    _advance(client, run_id, "extract")
    started = time.perf_counter()
    try:
        if execution_mode == "assisted":
            spec = resolve_edit_spec(prompt, sequence)
        else:
            edit_type = "CBE" if execution_mode == "demo_cbe" else "ABE"
            design = design_guide(sequence, edit_type)
            if design is None:
                raise AnalysisIssue("no_compatible_site")
            spec = EditSpec(
                edit_type=edit_type, **design,
                rationale=("Explicit rule-based demo: first compatible NGG site, guide positions "
                           "4–8. The run label is not interpreted as a biological objective. "
                           "No AI or retrieval was used; scores remain unvalidated heuristics."),
            )
    except Exception as exc:
        logger.warning("Run %s analysis failed (%s)", run_id, type(exc).__name__)
        issue = run_issue(
            "extract", exc.code if isinstance(exc, (AnalysisIssue, VaultSearchError))
            else "analysis_unavailable",
        )
        # Broad on purpose: resolve_edit_spec raises ValueError for a missing key,
        # bad JSON, or no guide site — but an OpenAI network/rate-limit error is a
        # different exception type entirely. Either way it belongs to "extract",
        # so it's classified here rather than falling through to a generic
        # unhandled-error path with no stage context.
        _halt(
            run_id,
            "extract",
            "analysis_failed",
            issue.message,
            payload={"failure": issue.model_dump()},
            duration_ms=_ms(started),
        )
    emit(
        run_id,
        "extract",
        "intent_resolved",
        ("Analysis agent resolved a candidate edit spec" if execution_mode == "assisted"
         else "Explicit rule-based demo selected the first compatible edit site"),
        payload={**_spec_payload(spec), "execution_mode": execution_mode},
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
    client.table("runs").update({"guide_rna": spec.guide_rna}).eq("run_id", run_id).execute()

    # ── simulate: deterministic base-edit engine ───────────────────────────
    _advance(client, run_id, "simulate")
    started = time.perf_counter()
    edit = apply_base_edit(
        sequence, spec.guide_rna, spec.edit_type, window=spec.window, pam=spec.pam
    )
    if not edit["edited"]:
        _halt(run_id, "simulate", "simulation_no_edit",
              run_issue("simulate", "simulation_no_edit").message)
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
    payload = dict(payload or {})
    issue = RunIssue.model_validate(payload["failure"]) if "failure" in payload else run_issue(
        stage, event_type,
    )
    if event_type == "schema_invalid":
        issue.details = [
            str(problem)[:200] for problem in payload.get("problems", [])[:10]
        ]
    payload["failure"] = issue.model_dump()
    emit(run_id, stage, event_type, message, payload=payload, duration_ms=duration_ms)
    raise _PipelineHalt(stage, issue)


def _advance(client, run_id: str, stage: str) -> None:
    """Move the run's current_stage marker so the UI tracks live progress."""
    client.table("runs").update({"current_stage": stage}).eq("run_id", run_id).execute()


def _finish(
    client, run_id: str, status: str, stage: str, failure: RunIssue | None = None,
) -> None:
    client.table("runs").update(
        {
            "status": status,
            "current_stage": stage,
            "completed_at": datetime.now(UTC).isoformat(),
            "failure": failure.model_dump() if failure else None,
        }
    ).eq("run_id", run_id).execute()


def _ms(started: float) -> int:
    return int((time.perf_counter() - started) * 1000)


def _spec_payload(spec: EditSpec) -> dict:
    return {
        "edit_type": spec.edit_type,
        "guide_rna": spec.guide_rna,
        "strand": spec.strand,
        "window": list(spec.window),
        "pam": spec.pam,
        "organism": spec.organism,
        "gene": spec.gene,
        "rationale": spec.rationale,
        "rag_sources": spec.rag_sources,
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
