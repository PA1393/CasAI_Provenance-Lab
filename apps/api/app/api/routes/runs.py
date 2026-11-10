from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import get_storage_backend
from app.core.config import settings
from app.db import get_supabase
from app.modules.runs.export import build_run_export
from app.modules.runs.service import (
    MAX_RUN_BASES,
    ConfirmedSourceError,
    RunInputError,
    RunInputNotFoundError,
    create_run,
    get_run,
    list_runs,
)
from app.schemas.runs import Run, RunCreate, RunsResponse

router = APIRouter(tags=["runs"])


@router.get("/demo/capabilities")
def demo_capabilities(storage_backend: str = Depends(get_storage_backend)) -> dict:
    return {
        "schema_version": "casai.demo-capabilities.v1",
        "run_execution_modes": ["assisted", "demo_cbe", "demo_abe"],
        "max_sequence_bases": MAX_RUN_BASES,
        "scientifically_validated": False,
        "personal_workspaces": settings.access_mode == "accounts",
        "access_mode": settings.access_mode,
        "authentication": "supabase-password" if settings.access_mode == "accounts" else "none",
        "storage_backend": storage_backend,
    }


@router.get("/runs/{run_id}/export")
def export_run(run_id: str) -> dict:
    try:
        package = build_run_export(run_id)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if package is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return package


@router.get("/runs", response_model=RunsResponse)
def get_runs() -> RunsResponse:
    return RunsResponse(items=[Run(**item) for item in list_runs()])


@router.get("/runs/metrics")
def run_metrics() -> dict:
    client = get_supabase()
    counts = {}
    for status in ("completed", "failed", "running", "queued"):
        response = (client.table("runs").select("run_id", count="exact", head=True)
                    .eq("status", status).execute())
        if type(response.count) is not int or response.count < 0:
            raise HTTPException(503, "Run statistics unavailable")
        counts[status] = response.count
    finished = counts["completed"] + counts["failed"]
    return {
        "completed": counts["completed"], "failed": counts["failed"], "finished": finished,
        "pending": counts["running"] + counts["queued"],
        "percent": round(counts["completed"] / finished * 100, 1) if finished else None,
        "meaning": "workflow_completion_only",
    }


@router.get("/runs/{run_id}", response_model=Run)
def get_run_by_id(run_id: str) -> Run:
    run = get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return Run(**run)


@router.post("/runs", response_model=Run, status_code=201)
def post_run(body: RunCreate) -> Run:
    try:
        run = create_run(
            research_object_id=body.research_object_id,
            prompt=body.prompt,
            execution_mode=body.execution_mode,
        )
    except ConfirmedSourceError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except RunInputNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RunInputError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return Run(**run)
