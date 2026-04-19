-- Migration 001: initial schema for CasAI Provenance Lab
-- Run this manually in the Supabase SQL editor.
-- Access is backend-only via the service role key — no anon RLS policies are created.
-- RLS is enabled to prevent accidental public exposure; policies will be added when auth is introduced.

-- ─── research_objects ────────────────────────────────────────────────────────

CREATE TABLE public.research_objects (
  research_object_id  UUID              PRIMARY KEY DEFAULT gen_random_uuid(),
  created_at          TIMESTAMPTZ       NOT NULL    DEFAULT now(),
  name                TEXT              NOT NULL,
  input_filename      TEXT              NOT NULL,
  input_file_type     TEXT              NOT NULL,
  pdb_id              TEXT              NOT NULL,
  mmcif_fetched_from  TEXT,
  mmcif_hash          TEXT,
  sequence_length     INT,
  gc_content          DOUBLE PRECISION,
  avg_phred_score     DOUBLE PRECISION,
  reads_passing_qc    INT,
  reads_total         INT,
  ro_hash             TEXT              NOT NULL,
  status              TEXT              NOT NULL
);

ALTER TABLE public.research_objects ENABLE ROW LEVEL SECURITY;

-- ─── runs ─────────────────────────────────────────────────────────────────────

CREATE TABLE public.runs (
  run_id              UUID              PRIMARY KEY DEFAULT gen_random_uuid(),
  research_object_id  UUID              NOT NULL
                        REFERENCES public.research_objects(research_object_id)
                        ON DELETE CASCADE,
  created_at          TIMESTAMPTZ       NOT NULL    DEFAULT now(),
  prompt              TEXT              NOT NULL,
  status              TEXT              NOT NULL,
  started_at          TIMESTAMPTZ,
  completed_at        TIMESTAMPTZ
);

ALTER TABLE public.runs ENABLE ROW LEVEL SECURITY;

-- ─── provenance_events ────────────────────────────────────────────────────────

CREATE TABLE public.provenance_events (
  event_id    UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  run_id      UUID        NOT NULL
                REFERENCES public.runs(run_id)
                ON DELETE CASCADE,
  occurred_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  event_type  TEXT        NOT NULL,
  message     TEXT        NOT NULL,
  payload     JSONB
);

ALTER TABLE public.provenance_events ENABLE ROW LEVEL SECURITY;

-- ─── results ─────────────────────────────────────────────────────────────────

CREATE TABLE public.results (
  result_id          UUID              PRIMARY KEY DEFAULT gen_random_uuid(),
  run_id             UUID              NOT NULL
                       REFERENCES public.runs(run_id)
                       ON DELETE CASCADE,
  research_object_id UUID              NOT NULL
                       REFERENCES public.research_objects(research_object_id)
                       ON DELETE CASCADE,
  created_at         TIMESTAMPTZ       NOT NULL DEFAULT now(),
  edited_sequence    TEXT              NOT NULL,
  edit_summary       TEXT              NOT NULL,
  off_target_score   DOUBLE PRECISION  NOT NULL,
  confidence         DOUBLE PRECISION  NOT NULL,
  notes              TEXT
);

ALTER TABLE public.results ENABLE ROW LEVEL SECURITY;
