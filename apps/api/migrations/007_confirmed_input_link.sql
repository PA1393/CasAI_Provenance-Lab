-- Additive bridge from immutable workspace confirmations to legacy run inputs.
-- Apply in Supabase before using "Use in a run"; no historical rows are changed.
ALTER TABLE public.research_objects
  ADD COLUMN IF NOT EXISTS confirmed_version_id TEXT,
  ADD COLUMN IF NOT EXISTS confirmed_record_id TEXT;

ALTER TABLE public.research_objects
  ADD CONSTRAINT research_objects_confirmed_source_pair CHECK (
    (confirmed_version_id IS NULL AND confirmed_record_id IS NULL) OR
    (confirmed_version_id IS NOT NULL AND confirmed_record_id IS NOT NULL
      AND confirmed_version_id ~ '^sha256:[0-9a-f]{64}$'
      AND length(confirmed_record_id) > 0)
  );

CREATE UNIQUE INDEX IF NOT EXISTS research_objects_confirmed_record_unique
  ON public.research_objects (confirmed_version_id, confirmed_record_id)
  WHERE confirmed_version_id IS NOT NULL;
