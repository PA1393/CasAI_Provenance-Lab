-- Migration 005: RAG similarity search function — v2.
-- Run once in the Supabase SQL editor, AFTER 004_vault_chunks_add_columns.sql.
--
-- Supersedes 003_match_vault_chunks.sql: same behaviour, but the returned row now
-- also includes the chunk's `heading` and `keywords` (added to vault_chunks in 004)
-- so retrieval surfaces section context and tags to the API and the LLM.
-- (Leave 003 in place — migrations are append-only; running this after it is a clean replace.)
--
-- Requires pgvector (already enabled). vault_sources is LEFT JOIN'd so retrieval still
-- works if a source row is missing. DROP first because CREATE OR REPLACE cannot change
-- the return-type signature.

drop function if exists public.match_vault_chunks(vector, double precision, integer);

create or replace function match_vault_chunks (
  query_embedding  vector(1536),
  match_threshold  float   default 0.0,
  match_count      int     default 3
)
returns table (
  chunk_id     uuid,
  source_key   text,
  chunk_text   text,
  heading      text,
  keywords     jsonb,
  metadata     jsonb,
  similarity   float,
  source_path  text,
  source_url   text,
  source_title text,
  source_type  text
)
language sql stable
as $$
  select
    vc.chunk_id,
    vc.source_key,
    vc.chunk_text,
    vc.heading,
    vc.keywords,
    vc.metadata,
    1 - (vc.embedding <=> query_embedding)          as similarity,
    coalesce(vs.source_path, vc.source_key)         as source_path,
    vs.source_url                                   as source_url,
    vs.source_title                                 as source_title,
    vs.source_type                                  as source_type
  from vault_chunks vc
  left join vault_sources vs using (source_key)
  where vc.embedding is not null
    and 1 - (vc.embedding <=> query_embedding) > match_threshold
  order by vc.embedding <=> query_embedding
  limit match_count;
$$;
