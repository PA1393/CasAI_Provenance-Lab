from __future__ import annotations

import logging

from openai import OpenAI

from app.core.config import settings
from app.db import get_supabase

logger = logging.getLogger(__name__)


def embed_query(text: str) -> list[float] | None:
    if not settings.openai_api_key:
        logger.warning("OPENAI_API_KEY not set — RAG search skipped")
        return None
    client = OpenAI(api_key=settings.openai_api_key)
    response = client.embeddings.create(model="text-embedding-3-small", input=text)
    return response.data[0].embedding


def search_vault(
    query: str,
    match_count: int = 3,
    match_threshold: float = 0.0,
) -> list[dict]:
    embedding = embed_query(query)
    if embedding is None:
        return []

    supabase = get_supabase()
    try:
        response = supabase.rpc(
            "match_vault_chunks",
            {
                "query_embedding": embedding,
                "match_threshold": match_threshold,
                "match_count": match_count,
            },
        ).execute()
        return response.data or []
    except Exception as exc:
        logger.warning("match_vault_chunks RPC failed: %s", exc)
        return []
