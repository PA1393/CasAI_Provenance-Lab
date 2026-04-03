from fastapi import APIRouter
from pydantic import BaseModel

from app.modules.runs.service import list_runs

router = APIRouter(tags=["runs"])


class RunSummary(BaseModel):
    id: str
    name: str
    status: str
    pipeline: str
    createdAt: str


class RunsResponse(BaseModel):
    items: list[RunSummary]


@router.get("/runs", response_model=RunsResponse)
def get_runs() -> RunsResponse:
    return RunsResponse(items=[RunSummary(**item) for item in list_runs()])
