# Handles GET /api/v1/runs — returns a list of runs. Data is fake/mock for now.
# Data shape is in schemas/runs.py; the data itself comes from modules/runs/service.py.

from fastapi import APIRouter

from app.modules.runs.service import list_runs
from app.schemas.runs import RunSummary, RunsResponse

router = APIRouter(tags=["runs"])


@router.get("/runs", response_model=RunsResponse)
def get_runs() -> RunsResponse:
    return RunsResponse(items=[RunSummary(**item) for item in list_runs()])
