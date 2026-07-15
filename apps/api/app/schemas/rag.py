from pydantic import BaseModel, Field, field_validator

from app.core.config import settings

_MAX_MATCH_COUNT = 5


class RagSearchRequest(BaseModel):
    query: str
    match_count: int = 3
    match_threshold: float = Field(default=settings.rag_match_threshold, ge=0.0, le=1.0)

    @field_validator("match_count")
    @classmethod
    def cap_match_count(cls, v: int) -> int:
        return min(v, _MAX_MATCH_COUNT)

class RagChunk(BaseModel):
    chunk_id: str
    source_key: str
    chunk_text: str
    metadata: dict | None = None
    similarity: float
    source_path: str | None = None
    source_url: str | None = None
    source_title: str | None = None
    source_type: str | None = None

class RagSearchResponse(BaseModel):
    items: list[RagChunk]

class RagAskRequest(RagSearchRequest):
    """Same fields and validation as RagSearchRequest; kept as its own
    type so the /rag/ask endpoint has a distinct schema to evolve
    independently if needed."""

class RagAskResponse(BaseModel):
    # `answer` is None when the OpenAI API key is missing, no matching
    # chunks were retrieved, or generation failed. Callers must handle
    # the null case rather than assuming an answer is always present.
    answer: str | None
    sources: list[RagChunk]
