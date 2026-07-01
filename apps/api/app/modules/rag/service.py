from __future__ import annotations

import logging

import google.generativeai as genai

from app.core.config import settings
from app.db import get_supabase

logger = logging.getLogger(__name__)


def embed_query(text: str) -> list[float] | None:
    """Return a 1536-dim embedding for *text* using Gemini text-embedding-004.
    Returns None if GEMINI_API_KEY is not configured."""
    if not settings.gemini_api_key:
        logger.warning("GEMINI_API_KEY not set — RAG search skipped")
        return None
    genai.configure(api_key=settings.gemini_api_key)
    result = genai.embed_content(
        model="models/gemini-embedding-001",
        content=text,
        output_dimensionality=1536,
    )
    return result["embedding"]


def search_vault(
    query: str,
    match_count: int = 6,
    match_threshold: float = 0.0,
) -> list[dict]:
    """
    Embed *query* then call the match_vault_chunks RPC in Supabase.

    Returns chunk dicts with keys: chunk_id, source_key, chunk_text, metadata, similarity.
    Returns an empty list gracefully when embeddings are unavailable or the RPC fails.
    """
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
