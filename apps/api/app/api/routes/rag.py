from fastapi import APIRouter

from app.modules.rag.service import answer_query, search_vault
from app.schemas.rag import (
    RagAskRequest,
    RagAskResponse,
    RagChunk,
    RagSearchRequest,
    RagSearchResponse,
)

router = APIRouter(tags=["rag"])


@router.post("/rag/search", response_model=RagSearchResponse)
def rag_search(body: RagSearchRequest) -> RagSearchResponse:
    chunks = search_vault(
        query=body.query,
        match_count=body.match_count,
        match_threshold=body.match_threshold,
    )
    return RagSearchResponse(items=[RagChunk(**c) for c in chunks])


@router.post("/rag/ask", response_model=RagAskResponse)
def rag_ask(body: RagAskRequest) -> RagAskResponse:
    result = answer_query(
        query=body.query,
        match_count=body.match_count,
        match_threshold=body.match_threshold,
    )
    return RagAskResponse(
        answer=result["answer"],
        sources=[RagChunk(**c) for c in result["sources"]],
    )
