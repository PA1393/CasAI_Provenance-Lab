-- Migration 007: B0 core contracts and database.
-- Apply after 006_research_object_sequence.sql.
--
-- Records are immutable versions. A logical source/artifact keeps its stable *_id;
-- each revision receives a new *_version_id and monotonically increasing version.
-- Customer-owned records are private by default. Commercial use is allowed only
-- through an active, explicit rights_grant for the exact run or versioned record.

CREATE TABLE IF NOT EXISTS public.source_records (
  source_version_id             UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  source_id                     UUID        NOT NULL DEFAULT gen_random_uuid(),
  version                       INTEGER     NOT NULL DEFAULT 1 CHECK (version >= 1),
  schema_version                INTEGER     NOT NULL DEFAULT 1 CHECK (schema_version >= 1),
  source_kind                   TEXT        NOT NULL CHECK (source_kind IN (
    'customer_upload', 'pasted_sequence', 'reference_accession',
    'curated_dataset', 'generated'
  )),
  owner_ref                     TEXT        NOT NULL CHECK (length(owner_ref) > 0),
  visibility                    TEXT        NOT NULL DEFAULT 'private'
                                            CHECK (visibility IN ('private', 'shared', 'public')),
  sha256                        TEXT        CHECK (sha256 IS NULL OR sha256 ~ '^[0-9a-f]{64}$'),
  locator                       JSONB,
  metadata                      JSONB       NOT NULL DEFAULT '{}'::jsonb,
  supersedes_source_version_id  UUID        REFERENCES public.source_records(source_version_id),
  created_at                    TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (source_id, version)
);

ALTER TABLE public.source_records ENABLE ROW LEVEL SECURITY;
CREATE INDEX IF NOT EXISTS source_records_source_id_idx
  ON public.source_records (source_id, version DESC);
CREATE INDEX IF NOT EXISTS source_records_owner_ref_idx
  ON public.source_records (owner_ref);

CREATE TABLE IF NOT EXISTS public.engine_versions (
  engine_version_id   UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  schema_version      INTEGER     NOT NULL DEFAULT 1 CHECK (schema_version >= 1),
  engine_name         TEXT        NOT NULL CHECK (length(engine_name) > 0),
  version             TEXT        NOT NULL CHECK (length(version) > 0),
  executable_digest   TEXT        CHECK (
    executable_digest IS NULL OR executable_digest ~ '^[0-9a-f]{64}$'
  ),
  capabilities        JSONB       NOT NULL DEFAULT '[]'::jsonb,
  enabled             BOOLEAN     NOT NULL DEFAULT true,
  created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (engine_name, version, executable_digest)
);

ALTER TABLE public.engine_versions ENABLE ROW LEVEL SECURITY;

CREATE TABLE IF NOT EXISTS public.artifact_records (
  artifact_version_id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  artifact_id                      UUID        NOT NULL DEFAULT gen_random_uuid(),
  version                          INTEGER     NOT NULL DEFAULT 1 CHECK (version >= 1),
  schema_version                   INTEGER     NOT NULL DEFAULT 1 CHECK (schema_version >= 1),
  artifact_type                    TEXT        NOT NULL CHECK (length(artifact_type) > 0),
  owner_ref                        TEXT        NOT NULL CHECK (length(owner_ref) > 0),
  visibility                       TEXT        NOT NULL DEFAULT 'private'
                                                CHECK (visibility IN ('private', 'shared', 'public')),
  sha256                           TEXT        NOT NULL CHECK (sha256 ~ '^[0-9a-f]{64}$'),
  byte_size                        BIGINT      NOT NULL CHECK (byte_size >= 0),
  media_type                       TEXT        NOT NULL CHECK (length(media_type) > 0),
  storage_uri                      TEXT        NOT NULL CHECK (length(storage_uri) > 0),
  run_id                           UUID        REFERENCES public.runs(run_id) ON DELETE CASCADE,
  source_version_id                UUID        REFERENCES public.source_records(source_version_id),
  engine_version_id                UUID        REFERENCES public.engine_versions(engine_version_id),
  supersedes_artifact_version_id   UUID        REFERENCES public.artifact_records(artifact_version_id),
  metadata                         JSONB       NOT NULL DEFAULT '{}'::jsonb,
  created_at                       TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (artifact_id, version)
);

ALTER TABLE public.artifact_records ENABLE ROW LEVEL SECURITY;
CREATE INDEX IF NOT EXISTS artifact_records_run_id_idx
  ON public.artifact_records (run_id);
CREATE INDEX IF NOT EXISTS artifact_records_source_version_id_idx
  ON public.artifact_records (source_version_id);

CREATE TABLE IF NOT EXISTS public.approvals (
  approval_id        UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  schema_version     INTEGER     NOT NULL DEFAULT 1 CHECK (schema_version >= 1),
  source_version_id  UUID        REFERENCES public.source_records(source_version_id),
  artifact_version_id UUID       REFERENCES public.artifact_records(artifact_version_id),
  run_id             UUID        REFERENCES public.runs(run_id) ON DELETE CASCADE,
  scope              TEXT        NOT NULL CHECK (
    scope IN ('input', 'plan', 'export', 'commercial_use')
  ),
  status             TEXT        NOT NULL DEFAULT 'draft' CHECK (
    status IN ('draft', 'submitted', 'approved', 'rejected', 'locked')
  ),
  requested_by       TEXT        NOT NULL CHECK (length(requested_by) > 0),
  decided_by         TEXT,
  decision_note      TEXT,
  submitted_at       TIMESTAMPTZ,
  decided_at         TIMESTAMPTZ,
  locked_at          TIMESTAMPTZ,
  created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
  CHECK (num_nonnulls(source_version_id, artifact_version_id, run_id) = 1)
);

ALTER TABLE public.approvals ENABLE ROW LEVEL SECURITY;
CREATE INDEX IF NOT EXISTS approvals_source_version_idx
  ON public.approvals (source_version_id, scope, created_at DESC);
CREATE INDEX IF NOT EXISTS approvals_artifact_version_idx
  ON public.approvals (artifact_version_id, scope, created_at DESC);
CREATE INDEX IF NOT EXISTS approvals_run_idx
  ON public.approvals (run_id, scope, created_at DESC);

CREATE TABLE IF NOT EXISTS public.rights_grants (
  rights_grant_id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  schema_version               INTEGER     NOT NULL DEFAULT 1 CHECK (schema_version >= 1),
  source_version_id            UUID        REFERENCES public.source_records(source_version_id),
  artifact_version_id          UUID        REFERENCES public.artifact_records(artifact_version_id),
  run_id                       UUID        REFERENCES public.runs(run_id) ON DELETE CASCADE,
  scope                        TEXT        NOT NULL CHECK (
    scope IN ('research_use', 'commercial_license')
  ),
  status                       TEXT        NOT NULL DEFAULT 'active'
                                           CHECK (status IN ('active', 'revoked')),
  permission_basis             TEXT        NOT NULL CHECK (permission_basis IN (
    'explicit_consent', 'customer_terms', 'public_license', 'owned', 'custom_agreement'
  )),
  explicit_permission          BOOLEAN     NOT NULL DEFAULT false,
  granted_by                   TEXT        NOT NULL CHECK (length(granted_by) > 0),
  evidence_artifact_version_id UUID        REFERENCES public.artifact_records(artifact_version_id),
  effective_at                 TIMESTAMPTZ NOT NULL DEFAULT now(),
  expires_at                   TIMESTAMPTZ,
  revoked_at                   TIMESTAMPTZ,
  created_at                   TIMESTAMPTZ NOT NULL DEFAULT now(),
  CHECK (num_nonnulls(source_version_id, artifact_version_id, run_id) = 1),
  CHECK (expires_at IS NULL OR expires_at > effective_at),
  CHECK (status <> 'revoked' OR revoked_at IS NOT NULL)
);

ALTER TABLE public.rights_grants ENABLE ROW LEVEL SECURITY;
CREATE INDEX IF NOT EXISTS rights_grants_source_version_idx
  ON public.rights_grants (source_version_id, scope, status);
CREATE INDEX IF NOT EXISTS rights_grants_artifact_version_idx
  ON public.rights_grants (artifact_version_id, scope, status);
CREATE INDEX IF NOT EXISTS rights_grants_run_idx
  ON public.rights_grants (run_id, scope, status);

-- Existing runs and events join the same versioned contract without rewriting history.
ALTER TABLE public.runs
  ADD COLUMN IF NOT EXISTS schema_version    INTEGER NOT NULL DEFAULT 1,
  ADD COLUMN IF NOT EXISTS run_version       INTEGER NOT NULL DEFAULT 1,
  ADD COLUMN IF NOT EXISTS plan_version      INTEGER NOT NULL DEFAULT 1,
  ADD COLUMN IF NOT EXISTS engine_version_id UUID REFERENCES public.engine_versions(engine_version_id);

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'runs_schema_version_positive') THEN
    ALTER TABLE public.runs
      ADD CONSTRAINT runs_schema_version_positive CHECK (schema_version >= 1);
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'runs_run_version_positive') THEN
    ALTER TABLE public.runs
      ADD CONSTRAINT runs_run_version_positive CHECK (run_version >= 1);
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'runs_plan_version_positive') THEN
    ALTER TABLE public.runs
      ADD CONSTRAINT runs_plan_version_positive CHECK (plan_version >= 1);
  END IF;
END $$;

ALTER TABLE public.provenance_events
  ADD COLUMN IF NOT EXISTS schema_version INTEGER NOT NULL DEFAULT 1,
  ADD COLUMN IF NOT EXISTS actor_type     TEXT NOT NULL DEFAULT 'system'
                                          CHECK (actor_type IN ('system', 'user', 'engine')),
  ADD COLUMN IF NOT EXISTS actor_ref      TEXT;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'provenance_events_schema_version_positive'
  ) THEN
    ALTER TABLE public.provenance_events
      ADD CONSTRAINT provenance_events_schema_version_positive CHECK (schema_version >= 1);
  END IF;
END $$;

-- This view is deliberately strict: visibility alone never makes data sellable.
-- B7 may consume it when curating a versioned CasAI dataset.
CREATE OR REPLACE VIEW public.commercially_rights_cleared_records AS
SELECT
  rights_grant_id,
  source_version_id,
  artifact_version_id,
  run_id,
  permission_basis,
  evidence_artifact_version_id,
  effective_at,
  expires_at
FROM public.rights_grants
WHERE scope = 'commercial_license'
  AND status = 'active'
  AND explicit_permission = true
  AND effective_at <= now()
  AND (expires_at IS NULL OR expires_at > now())
  AND revoked_at IS NULL;
