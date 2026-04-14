from fastapi import APIRouter

from app.modules.results.service import list_results
from app.schemas.results import Result, ResultsResponse

router = APIRouter(tags=["results"])


@router.get("/runs/{run_id}/results", response_model=ResultsResponse)
def get_results(run_id: str) -> ResultsResponse:
    return ResultsResponse(
        items=[Result(**result) for result in list_results(run_id)]
    )
