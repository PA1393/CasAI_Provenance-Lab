from fastapi import APIRouter, HTTPException

from app.modules.research_objects.service import (
    create_research_object,
    get_research_object,
    list_research_objects,
)
from app.schemas.research_objects import ResearchObject, ResearchObjectCreate, ResearchObjectsResponse

router = APIRouter(tags=["research_objects"])


@router.get("/research-objects", response_model=ResearchObjectsResponse)
def get_research_objects() -> ResearchObjectsResponse:
    return ResearchObjectsResponse(
        items=[ResearchObject(**item) for item in list_research_objects()]
    )


@router.post("/research-objects", response_model=ResearchObject, status_code=201)
def post_research_object(body: ResearchObjectCreate) -> ResearchObject:
    created = create_research_object(body.model_dump(exclude_none=True))
    return ResearchObject(**created)


@router.get("/research-objects/{research_object_id}", response_model=ResearchObject)
def get_research_object_by_id(research_object_id: str) -> ResearchObject:
    item = get_research_object(research_object_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Research object not found")
    return ResearchObject(**item)
