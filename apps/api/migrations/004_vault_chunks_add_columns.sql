-- Migration 004: add usability columns to vault_chunks.
-- Run manually in the Supabase SQL editor after 003_match_vault_chunks.sql.
--
-- Additive only (ADD COLUMN IF NOT EXISTS) — existing rows, embeddings, and the
-- 3 currently-populated chunks are left completely untouched.
--
--   heading  — nearest Markdown heading above the chunk (section context used for
--              grounding and citation labels)
--   keywords — tags derived from the source note's frontmatter
--              (crop/organism, techniques, gene_target, editing_method)
--
-- Both columns are nullable: existing chunks simply return NULL for them, and no
-- re-embedding is required (embeddings derive from chunk_text, which is unchanged).

alter table public.vault_chunks
  add column if not exists heading   text,
  add column if not exists keywords  jsonb;
