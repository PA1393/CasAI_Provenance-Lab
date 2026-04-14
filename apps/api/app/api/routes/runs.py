from fastapi import APIRouter

from app.modules.runs.service import list_runs
from app.schemas.runs import RunSummary, RunsResponse

router = APIRouter(tags=["runs"])


@router.get("/runs", response_model=RunsResponse)
def get_runs() -> RunsResponse:
    return RunsResponse(items=[RunSummary(**item) for item in list_runs()])
