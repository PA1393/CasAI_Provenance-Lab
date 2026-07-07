from pydantic import BaseModel, field_validator

_MAX_MATCH_COUNT = 5


class RagSearchRequest(BaseModel):
    query: str
    match_count: int = 3
    match_threshold: float = 0.0

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


class RagAskRequest(BaseModel):
    query: str
    match_count: int = 3
    match_threshold: float = 0.0

    @field_validator("match_count")
    @classmethod
    def cap_match_count(cls, v: int) -> int:
        return min(v, _MAX_MATCH_COUNT)


class RagAskResponse(BaseModel):
    answer: str | None
    sources: list[RagChunk]
