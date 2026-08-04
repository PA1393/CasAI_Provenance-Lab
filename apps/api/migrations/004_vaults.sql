-- Migration 004: codify vault tables + add vault labeling
-- Run once in the Supabase SQL editor.
--
-- vault_chunks / vault_sources already exist in Supabase (created by hand, never
-- migrated). This file first codifies them as they exist today so the schema lives
-- in the repo, then adds a `vault` column so chunks can be scoped to a named vault
-- (e.g. "crop", "human"). CREATE TABLE uses IF NOT EXISTS so this is safe to run
-- against the live database without disturbing existing data.
--
-- Demo scope: only the "crop" vault is populated right now. Every existing row is
-- backfilled to 'crop' below; new vaults are added later by inserting rows with a
-- different `vault` value — no schema change needed at that point.

-- ─── vault_chunks ───────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS public.vault_chunks (
  chunk_id     UUID              PRIMARY KEY DEFAULT extensions.gen_random_uuid(),
  source_key   TEXT              NOT NULL,
  chunk_index  INTEGER           NOT NULL,
  chunk_text   TEXT              NOT NULL,
  token_count  INTEGER,
  metadata     JSONB             NOT NULL DEFAULT '{}'::jsonb,
  embedding    vector(1536),
  heading      TEXT,
  keywords     JSONB,
  created_at   TIMESTAMPTZ       NOT NULL DEFAULT now()
);

-- ─── vault_sources ──────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS public.vault_sources (
  source_key     TEXT              PRIMARY KEY,
  source_title   TEXT,
  source_url     TEXT,
  source_type    TEXT,
  source_path    TEXT,
  source_rel     TEXT,
  organism       TEXT,
  gene_target    TEXT,
  editing_method TEXT,
  quality_label  TEXT,
  metadata       JSONB             NOT NULL DEFAULT '{}'::jsonb,
  created_at     TIMESTAMPTZ       NOT NULL DEFAULT now(),
  updated_at     TIMESTAMPTZ       NOT NULL DEFAULT now()
);

-- ─── vault labeling ─────────────────────────────────────────────────────────────
-- stage NOT NULL pattern mirrors 002_phase1_schema.sql: add nullable, backfill,
-- then enforce NOT NULL so this is safe against existing rows.

ALTER TABLE public.vault_chunks
  ADD COLUMN IF NOT EXISTS vault TEXT;

UPDATE public.vault_chunks SET vault = 'crop' WHERE vault IS NULL;

ALTER TABLE public.vault_chunks ALTER COLUMN vault SET NOT NULL;
ALTER TABLE public.vault_chunks ALTER COLUMN vault SET DEFAULT 'crop';

CREATE INDEX IF NOT EXISTS vault_chunks_vault_idx ON public.vault_chunks (vault);
