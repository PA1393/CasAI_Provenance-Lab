-- Migration 003: RAG similarity search function
-- Run once in the Supabase SQL editor.
-- Requires pgvector (already enabled — vault_chunks uses vector(1536)).
-- vault_sources is LEFT JOIN'd so retrieval still works if a source row is missing.
-- DROP first because CREATE OR REPLACE cannot change the return-type signature.

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
