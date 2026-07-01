-- Migration 003: RAG similarity search function
-- Run once in the Supabase SQL editor.
-- Requires pgvector (already enabled — vault_chunks uses vector(1536)).

create or replace function match_vault_chunks (
  query_embedding  vector(1536),
  match_threshold  float   default 0.70,
  match_count      int     default 10
)
returns table (
  chunk_id    uuid,
  source_key  text,
  chunk_text  text,
  metadata    jsonb,
  similarity  float
)
language sql stable
as $$
  select
    chunk_id,
    source_key,
    chunk_text,
    metadata,
    1 - (embedding <=> query_embedding) as similarity
  from vault_chunks
  where embedding is not null
    and 1 - (embedding <=> query_embedding) > match_threshold
  order by embedding <=> query_embedding
  limit match_count;
$$;
