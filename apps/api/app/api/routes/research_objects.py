# Handles GET /api/v1/research-objects — returns a list of research objects. Data is fake/mock for now.
# Data shape is in schemas/research_objects.py; the data itself comes from modules/research_objects/service.py.

from fastapi import APIRouter

from app.modules.research_objects.service import list_research_objects
from app.schemas.research_objects import ResearchObject, ResearchObjectsResponse

router = APIRouter(tags=["research_objects"])


@router.get("/research-objects", response_model=ResearchObjectsResponse)
def get_research_objects() -> ResearchObjectsResponse:
    return ResearchObjectsResponse(
        items=[ResearchObject(**item) for item in list_research_objects()]
    )
