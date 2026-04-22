from fastapi import APIRouter, HTTPException

from app.modules.runs.service import create_run, get_run, list_runs
from app.schemas.runs import Run, RunCreate, RunsResponse

router = APIRouter(tags=["runs"])


@router.get("/runs", response_model=RunsResponse)
def get_runs() -> RunsResponse:
    return RunsResponse(items=[Run(**item) for item in list_runs()])


@router.get("/runs/{run_id}", response_model=Run)
def get_run_by_id(run_id: str) -> Run:
    run = get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return Run(**run)


@router.post("/runs", response_model=Run, status_code=201)
def post_run(body: RunCreate) -> Run:
    run = create_run(
        research_object_id=body.research_object_id,
        prompt=body.prompt,
    )
    return Run(**run)
