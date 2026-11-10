-- Run after 001–007. 008 is OPTIONAL while accounts are deferred.
-- Adds empty demo tables; never copies, publishes or deletes personal/legacy rows.
BEGIN;
ALTER TABLE public.runs ADD COLUMN IF NOT EXISTS failure jsonb;

CREATE TABLE public.demo_research_objects
  (LIKE public.research_objects INCLUDING DEFAULTS INCLUDING CONSTRAINTS);
ALTER TABLE public.demo_research_objects ADD PRIMARY KEY(research_object_id);
ALTER TABLE public.demo_research_objects DROP COLUMN IF EXISTS owner_id;
ALTER TABLE public.demo_research_objects ADD COLUMN IF NOT EXISTS folder_id uuid;
CREATE TABLE public.demo_runs (LIKE public.runs INCLUDING DEFAULTS INCLUDING CONSTRAINTS);
ALTER TABLE public.demo_runs ADD PRIMARY KEY(run_id);
ALTER TABLE public.demo_runs DROP COLUMN IF EXISTS owner_id;
ALTER TABLE public.demo_runs ADD COLUMN IF NOT EXISTS folder_id uuid;
CREATE TABLE public.demo_results (LIKE public.results INCLUDING DEFAULTS INCLUDING CONSTRAINTS);
ALTER TABLE public.demo_results ADD PRIMARY KEY(result_id);
CREATE TABLE public.demo_provenance_events
  (LIKE public.provenance_events INCLUDING DEFAULTS INCLUDING CONSTRAINTS);
ALTER TABLE public.demo_provenance_events ADD PRIMARY KEY(event_id);
CREATE TABLE public.demo_research_folders (
  folder_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name text NOT NULL CHECK(length(btrim(name)) BETWEEN 1 AND 100),
  created_at timestamptz NOT NULL DEFAULT now()
);
ALTER TABLE public.demo_research_objects ADD FOREIGN KEY(folder_id)
  REFERENCES public.demo_research_folders(folder_id);
ALTER TABLE public.demo_runs ADD FOREIGN KEY(folder_id)
  REFERENCES public.demo_research_folders(folder_id);
ALTER TABLE public.demo_runs ADD FOREIGN KEY(research_object_id)
  REFERENCES public.demo_research_objects(research_object_id);
ALTER TABLE public.demo_results ADD FOREIGN KEY(run_id) REFERENCES public.demo_runs(run_id);
ALTER TABLE public.demo_results ADD FOREIGN KEY(research_object_id)
  REFERENCES public.demo_research_objects(research_object_id);
ALTER TABLE public.demo_provenance_events ADD FOREIGN KEY(run_id)
  REFERENCES public.demo_runs(run_id);
ALTER TABLE public.demo_research_objects ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.demo_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.demo_results ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.demo_provenance_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.demo_research_folders ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.demo_research_objects, public.demo_runs, public.demo_results,
  public.demo_provenance_events, public.demo_research_folders FROM PUBLIC, anon, authenticated;
GRANT SELECT, INSERT, UPDATE ON public.demo_research_objects, public.demo_runs,
  public.demo_results, public.demo_provenance_events, public.demo_research_folders TO service_role;
COMMIT;
