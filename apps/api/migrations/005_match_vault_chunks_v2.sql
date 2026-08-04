-- Migration 005: add vault filtering to match_vault_chunks
-- Run once in the Supabase SQL editor.
-- Requires 004_vaults.sql to have run first (adds vault_chunks.vault).
-- DROP first because CREATE OR REPLACE cannot change the return-type signature
-- (same reason 003 dropped the unfiltered version before it).
--
-- vault_filter is optional (default null = search all vaults, same behavior as
-- before this migration). Demo scope: only 'crop' is populated, so callers pass
-- vault_filter => array['crop'] for now; a second vault later is just a different
-- array value, no further schema change needed.

drop function if exists public.match_vault_chunks(vector, double precision, integer);

create or replace function match_vault_chunks (
  query_embedding  vector(1536),
  match_threshold  float    default 0.0,
  match_count      int      default 3,
  vault_filter     text[]   default null
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
  source_type  text,
  vault        text
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
    vs.source_type                                  as source_type,
    vc.vault                                        as vault
  from vault_chunks vc
  left join vault_sources vs using (source_key)
  where vc.embedding is not null
    and 1 - (vc.embedding <=> query_embedding) > match_threshold
    and (vault_filter is null or vc.vault = any(vault_filter))
  order by vc.embedding <=> query_embedding
  limit match_count;
$$;
