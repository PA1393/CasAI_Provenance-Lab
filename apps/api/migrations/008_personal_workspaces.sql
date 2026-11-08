-- Apply once AFTER 007, before deploying the authenticated app. Transactional.
-- No legacy row is deleted or assigned to an arbitrary user. NULL owners stay hidden.
BEGIN;

CREATE TABLE public.research_folders (
  folder_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  owner_id uuid NOT NULL DEFAULT auth.uid() REFERENCES auth.users(id),
  name text NOT NULL CHECK (length(btrim(name)) BETWEEN 1 AND 100),
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(owner_id, folder_id)
);
ALTER TABLE public.research_folders ENABLE ROW LEVEL SECURITY;

ALTER TABLE public.research_objects ADD COLUMN owner_id uuid REFERENCES auth.users(id);
ALTER TABLE public.research_objects ALTER COLUMN owner_id SET DEFAULT auth.uid();
ALTER TABLE public.research_objects ADD COLUMN folder_id uuid;
ALTER TABLE public.research_objects ADD UNIQUE(owner_id, research_object_id);
ALTER TABLE public.research_objects ADD FOREIGN KEY(owner_id, folder_id)
  REFERENCES public.research_folders(owner_id, folder_id);
ALTER TABLE public.runs ADD COLUMN owner_id uuid REFERENCES auth.users(id);
ALTER TABLE public.runs ALTER COLUMN owner_id SET DEFAULT auth.uid();
ALTER TABLE public.runs ADD COLUMN folder_id uuid;
ALTER TABLE public.runs ADD FOREIGN KEY(owner_id, folder_id)
  REFERENCES public.research_folders(owner_id, folder_id);
ALTER TABLE public.runs ADD FOREIGN KEY(owner_id, research_object_id)
  REFERENCES public.research_objects(owner_id, research_object_id);
CREATE INDEX research_objects_owner_idx ON public.research_objects(owner_id, folder_id);
CREATE INDEX runs_owner_idx ON public.runs(owner_id, folder_id);

-- A restrictive guard remains effective even if an older permissive policy exists.
CREATE POLICY folder_access ON public.research_folders TO authenticated
  USING (owner_id = auth.uid()) WITH CHECK (owner_id = auth.uid());
CREATE POLICY folder_guard ON public.research_folders AS RESTRICTIVE TO authenticated
  USING (owner_id = auth.uid()) WITH CHECK (owner_id = auth.uid());
CREATE POLICY research_access ON public.research_objects TO authenticated
  USING (owner_id = auth.uid()) WITH CHECK (owner_id = auth.uid());
CREATE POLICY research_guard ON public.research_objects AS RESTRICTIVE TO authenticated
  USING (owner_id = auth.uid()) WITH CHECK (owner_id = auth.uid());
CREATE POLICY run_access ON public.runs TO authenticated
  USING (owner_id = auth.uid()) WITH CHECK (owner_id = auth.uid());
CREATE POLICY run_guard ON public.runs AS RESTRICTIVE TO authenticated
  USING (owner_id = auth.uid()) WITH CHECK (owner_id = auth.uid());

CREATE POLICY provenance_access ON public.provenance_events TO authenticated
  USING (EXISTS (SELECT 1 FROM public.runs r WHERE r.run_id = provenance_events.run_id))
  WITH CHECK (EXISTS (SELECT 1 FROM public.runs r WHERE r.run_id = provenance_events.run_id));
CREATE POLICY provenance_guard ON public.provenance_events AS RESTRICTIVE TO authenticated
  USING (EXISTS (SELECT 1 FROM public.runs r WHERE r.run_id = provenance_events.run_id))
  WITH CHECK (EXISTS (SELECT 1 FROM public.runs r WHERE r.run_id = provenance_events.run_id));
CREATE POLICY result_access ON public.results TO authenticated
  USING (EXISTS (SELECT 1 FROM public.runs r WHERE r.run_id = results.run_id
    AND r.research_object_id = results.research_object_id))
  WITH CHECK (EXISTS (SELECT 1 FROM public.runs r WHERE r.run_id = results.run_id
    AND r.research_object_id = results.research_object_id));
CREATE POLICY result_guard ON public.results AS RESTRICTIVE TO authenticated
  USING (EXISTS (SELECT 1 FROM public.runs r WHERE r.run_id = results.run_id
    AND r.research_object_id = results.research_object_id))
  WITH CHECK (EXISTS (SELECT 1 FROM public.runs r WHERE r.run_id = results.run_id
    AND r.research_object_id = results.research_object_id));

-- No anonymous access, even if an old policy or default grant exists.
REVOKE ALL ON public.research_folders, public.research_objects, public.runs,
  public.results, public.provenance_events FROM anon, authenticated, PUBLIC;
GRANT SELECT, INSERT, UPDATE ON public.research_folders, public.research_objects,
  public.runs, public.results, public.provenance_events TO authenticated;
COMMIT;
