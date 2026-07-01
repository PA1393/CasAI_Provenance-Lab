"""
One-off script: fills in NULL embeddings for every row in vault_chunks
using Gemini's text-embedding-004 model (1536 dims to match the column).

Run from apps/api with the venv active:
    .venv\\Scripts\\python.exe scripts\\backfill_embeddings.py
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import google.generativeai as genai

from app.core.config import settings
from app.db import get_supabase


def main() -> None:
    if not settings.gemini_api_key:
        print("GEMINI_API_KEY is not set in .env — aborting.")
        return
    if not settings.supabase_url or not settings.supabase_service_key:
        print("SUPABASE_URL / SUPABASE_SERVICE_KEY are not set in .env — aborting.")
        return

    genai.configure(api_key=settings.gemini_api_key)
    supabase = get_supabase()

    response = (
        supabase.table("vault_chunks")
        .select("chunk_id, chunk_text")
        .is_("embedding", "null")
        .execute()
    )
    rows = response.data or []
    print(f"Found {len(rows)} chunks missing embeddings.")

    for i, row in enumerate(rows, start=1):
        chunk_id = row["chunk_id"]
        text = row["chunk_text"]
        result = genai.embed_content(
            model="models/gemini-embedding-001",
            content=text,
            output_dimensionality=1536,
        )
        embedding = result["embedding"]
        supabase.table("vault_chunks").update({"embedding": embedding}).eq(
            "chunk_id", chunk_id
        ).execute()
        print(f"[{i}/{len(rows)}] embedded chunk {chunk_id}")
        time.sleep(0.2)

    print("Done.")


if __name__ == "__main__":
    main()
