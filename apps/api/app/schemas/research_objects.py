# Defines what a "research object" looks like when the API sends it back — the fields and their types.
# The metadata and hash fields are rough placeholders; the real structure gets decided once we know how inputs are parsed.

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
