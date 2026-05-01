


-- gotta run this in supabase 
-- Migration 002: Phase 1 domain model alignment
-- Run this manually in the Supabase SQL editor after 001_init.sql.
-- All changes are additive (ADD COLUMN / RENAME COLUMN) — existing rows are safe.

-- ─── research_objects ────────────────────────────────────────────────────────
-- fasta_preview: a short text snippet of the uploaded sequence, shown in the UI
-- target_region: [start, end] coordinates of the CRISPR target site (stored as jsonb array)

ALTER TABLE public.research_objects
  ADD COLUMN IF NOT EXISTS fasta_preview   TEXT,
  ADD COLUMN IF NOT EXISTS target_region   JSONB;

-- ─── runs ─────────────────────────────────────────────────────────────────────
-- guide_rna:     the 20-nt guide RNA sequence used to direct the CRISPR cut
-- current_stage: which pipeline stage the run is currently in (null = not started)

ALTER TABLE public.runs
  ADD COLUMN IF NOT EXISTS guide_rna      TEXT,
  ADD COLUMN IF NOT EXISTS current_stage  TEXT;

-- ─── provenance_events ────────────────────────────────────────────────────────
-- stage:       which pipeline stage emitted this event (preflight/extract/simulate/score/summary)
-- duration_ms: how long this event took in milliseconds (useful for timing display)

ALTER TABLE public.provenance_events
  ADD COLUMN IF NOT EXISTS stage        TEXT,
  ADD COLUMN IF NOT EXISTS duration_ms  INTEGER;

-- Backfill stage for any existing rows so NOT NULL can be enforced going forward.
-- "legacy" is a safe sentinel that the frontend can handle gracefully.
UPDATE public.provenance_events SET stage = 'legacy' WHERE stage IS NULL;

ALTER TABLE public.provenance_events ALTER COLUMN stage SET NOT NULL;

CREATE INDEX IF NOT EXISTS provenance_events_stage_idx ON public.provenance_events (stage);

-- ─── results ─────────────────────────────────────────────────────────────────
-- confidence → on_target_score: more precise CRISPR terminology for the same value
-- reproducible: audit flag — true means the run can be re-run and produce the same result

ALTER TABLE public.results
  RENAME COLUMN confidence TO on_target_score;

ALTER TABLE public.results
  ADD COLUMN IF NOT EXISTS reproducible BOOLEAN NOT NULL DEFAULT true;
