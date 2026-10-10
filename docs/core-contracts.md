# B0 core contracts

B0 establishes the records shared by every later package. The contract schema starts at
version `1`; records carry `schema_version` so readers can reject or migrate incompatible
payloads deliberately.

## Records

- **Run** — stable `run_id`, `run_version`, `plan_version`, and optional exact engine version.
- **Source** — a logical `source_id` with immutable `source_version_id` revisions.
- **Artifact** — a logical `artifact_id` with immutable, hashed `artifact_version_id` revisions.
- **Engine version** — the exact engine name, version, executable digest, and capabilities.
- **Approval** — a scoped decision targeting one run, source, or artifact.
- **Rights grant** — permission targeting exactly one run or immutable source/artifact version.
- **Provenance event** — a schema-versioned fact emitted by the pipeline.

Source and artifact visibility defaults to `private`. Visibility is access state, not a license.
Public or shared data does not automatically become commercially usable.

## Commercial-rights invariant

A record can enter a future sellable CasAI dataset only when its exact run or immutable
version has an active `commercial_license` grant with `explicit_permission = true`. The
grant must be effective, unexpired, and unrevoked. Migration 007 exposes the strict
`commercially_rights_cleared_records` view for B7; the Python rights service applies the
same rule before export or curation.

## Package boundaries

B0 defines the shared records and invariants. It intentionally does not implement:

- parsing and accession resolution (B1)
- guide/enzyme mapping (B2/B3)
- orchestration jobs and retries (B4)
- molecular scene generation (B5)
- organization roles or approval-gated execution (B6)
- export bundles or dataset assembly (B7)

Apply `apps/api/migrations/007_core_contracts.sql` after migration 006.
