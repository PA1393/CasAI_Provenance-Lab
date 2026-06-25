import os
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI
from supabase import create_client


EMBEDDING_MODEL = "text-embedding-3-small"
EXPECTED_DIMENSIONS = 1536


def require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def main() -> None:
    load_dotenv()
    print("Starting embed_vault_chunks script...")

    openai_api_key = require_env("OPENAI_API_KEY")
    supabase_url = require_env("SUPABASE_URL")
    supabase_key = require_env("SUPABASE_SERVICE_KEY")

    print(f"OPENAI_API_KEY: {'set' if openai_api_key else 'MISSING'}")
    print(f"SUPABASE_URL: {'set' if supabase_url else 'MISSING'}")
    print(f"SUPABASE_SERVICE_KEY: {'set' if supabase_key else 'MISSING'}")

    openai_client = OpenAI(api_key=openai_api_key)
    print("OpenAI client created.")

    supabase = create_client(supabase_url, supabase_key)
    print("Supabase client created.")

    response = (
        supabase.table("vault_chunks")
        .select("chunk_id, chunk_text")
        .is_("embedding", "null")
        .execute()
    )

    rows: list[dict[str, Any]] = response.data or []

    if not rows:
        print("No chunks need embeddings.")
        return

    print(f"Found {len(rows)} chunks without embeddings.")

    for row in rows:
        chunk_id = row["chunk_id"]
        chunk_text = row["chunk_text"]

        if not chunk_text or not chunk_text.strip():
            print(f"Skipping empty chunk: {chunk_id}")
            continue

        embedding_response = openai_client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=chunk_text,
        )

        embedding = embedding_response.data[0].embedding

        if len(embedding) != EXPECTED_DIMENSIONS:
            raise RuntimeError(
                f"Expected {EXPECTED_DIMENSIONS} dimensions, got {len(embedding)}"
            )

        (
            supabase.table("vault_chunks")
            .update({"embedding": embedding})
            .eq("chunk_id", chunk_id)
            .execute()
        )

        print(f"Updated embedding for chunk_id={chunk_id}")

    print("Done embedding vault chunks.")


if __name__ == "__main__":
    main()