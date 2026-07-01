from pydantic import BaseModel


class RagSearchRequest(BaseModel):
    query: str
    match_count: int = 6
    match_threshold: float = 0.0


class RagChunk(BaseModel):
    chunk_id: str
    source_key: str
    chunk_text: str
    metadata: dict | None = None
    similarity: float


class RagSearchResponse(BaseModel):
    items: list[RagChunk]
