from fastapi import APIRouter

from app.modules.rag.service import search_vault
from app.schemas.rag import RagChunk, RagSearchRequest, RagSearchResponse

router = APIRouter(tags=["rag"])


@router.post("/rag/search", response_model=RagSearchResponse)
def rag_search(body: RagSearchRequest) -> RagSearchResponse:
    chunks = search_vault(
        query=body.query,
        match_count=body.match_count,
        match_threshold=body.match_threshold,
    )
    return RagSearchResponse(items=[RagChunk(**c) for c in chunks])
