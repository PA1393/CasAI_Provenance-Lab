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
    try:
        client = OpenAI(api_key=settings.openai_api_key)
        response = client.embeddings.create(model="text-embedding-3-small", input=text)
        return response.data[0].embedding
    except Exception as exc:
        logger.warning("query embedding failed: %s", exc)
        return None


def search_vault(
    query: str,
    match_count: int = 3,
    match_threshold: float = 0.2,
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


_SYSTEM_PROMPT = (
    "You are a CRISPR / base-editing research assistant for the CasAI Provenance Lab. "
    "Answer the user's question using ONLY the numbered context passages provided. "
    "Cite the passages you rely on inline using bracketed numbers like [1] or [2]. "
    "If the context does not contain enough information to answer, say so plainly "
    "instead of guessing. Keep the answer concise and grounded."
)


def _format_context(chunks: list[dict]) -> str:
    """Render retrieved chunks as a numbered, citable context block."""
    blocks = []
    for i, chunk in enumerate(chunks, start=1):
        label = (
            chunk.get("source_title")
            or chunk.get("source_path")
            or chunk.get("source_key")
            or "source"
        )
        heading = chunk.get("heading")
        if heading:
            label = f"{label} — {heading}"
        text = (chunk.get("chunk_text") or "").strip()
        blocks.append(f"[{i}] {label}\n{text}")
    return "\n\n".join(blocks)


def generate_answer(query: str, chunks: list[dict]) -> str | None:
    """
    Generate a grounded natural-language answer for *query* from retrieved *chunks*.

    Returns None when generation is unavailable (no API key) or when there is no
    context to ground on. Never raises — a failed generation must not break a run.
    """
    if not settings.openai_api_key:
        logger.warning("OPENAI_API_KEY not set — answer generation skipped")
        return None
    if not chunks:
        return None

    client = OpenAI(api_key=settings.openai_api_key)
    context = _format_context(chunks)
    try:
        response = client.chat.completions.create(
            model=settings.openai_chat_model,
            temperature=0.2,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": f"Question:\n{query}\n\nContext:\n{context}",
                },
            ],
        )
        return (response.choices[0].message.content or "").strip() or None
    except Exception as exc:
        logger.warning("answer generation failed: %s", exc)
        return None


def answer_query(
    query: str,
    match_count: int = 3,
    match_threshold: float = 0.2,
) -> dict:
    """Retrieve context then generate a grounded answer. Returns answer + sources."""
    chunks = search_vault(
        query=query,
        match_count=match_count,
        match_threshold=match_threshold,
    )
    answer = generate_answer(query, chunks)
    return {"answer": answer, "sources": chunks}
