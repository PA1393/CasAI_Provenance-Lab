from pydantic import BaseModel


class ResearchObject(BaseModel):
    research_object_id: str
    sequence_data: str
    metadata: dict[str, str]
    structure_reference: str | None = None
    # Conceptually stable hash of the normalized input
    hash: str


class ResearchObjectsResponse(BaseModel):
    items: list[ResearchObject]
