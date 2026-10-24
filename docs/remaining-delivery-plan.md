# Combined delivery plan and PR audit

Reviewed against the build brief, implementation request, repository contracts,
and code on 2026-10-20. Kavin now owns the remaining implementation previously
allocated to the second contributor. Continue work on `KavNewPR` in PR #56.
This records an expanded delivery scope, not a claim that all milestones are done.

## Verified repository inventory

- `information_processor`: typed sequence, FASTQ/VCF and PDB/mmCIF inspection,
  supplied-reference verification, immutable local drafts and sequence confirmation.
- `/api/v1/intake`: detection, bounded inspection, local sequence draft storage,
  missing-field inspection and confirmation. The richer API is separate from the
  legacy Supabase research-object/run workflow used by the UI.
- `guide_mapping`: confirmed-input binding, both strands, PAMs, edit windows,
  desired edits, bystanders, transparent heuristic ranking, local persistence/API.
- `simulation`: deterministic plan contracts, exact engine dispatch, required and
  optional stages, in-process execution attempts, retry and cancellation lineage.
  The public plan API creates drafts only; executable sessions are not persisted.
- `scene_manifest`: bounded declarative assets, selections, units, annotations,
  transforms, camera/visibility states, content identity and local persistence/API.
- `integrations`: explicit external tool adapters exist; availability, references,
  real runtime execution and binding to approved plans still need integration.
- `private_data_security`: evidence-based readiness contracts and policy functions
  exist. The required production controls do not exist, and this is not an
  enforcement middleware on every legacy route. The demo is for non-sensitive data.
- `apps/web`: legacy FASTA upload/review, research-object lists, run creation,
  provenance/results and a Mol* public-example viewer. This PR adds a shared
  workbench, consistent navigation, light/dark tokens and a persistent theme switch.
- `apps/desktop`: bundled React/Tauri client, scoped native API transport,
  backend compatibility gate and three-platform packaging workflow. The Mac
  app builds and launches locally. Full latest-backend rehearsal, Windows/Linux
  interactive launch verification and public-release signing remain incomplete;
  see `desktop-demo.md` for precise evidence and deployment blockers.

## PR review findings addressed in this increment

1. Legacy creation overwrote the user's target window with `[720, 742]` and the
   UI requested zero-based coordinates. Keep exact 1-based inclusive endpoints,
   accept single-base windows, reject malformed/out-of-sequence coordinates, and
   leave omitted windows absent. Validate API input before numeric coercion.
2. Legacy creation fabricated sequence length, QC counts, structure retrieval and
   hashes. Unmeasured fields now remain null, absent-sequence records stay drafts,
   and explicitly empty uploads fail validation.
3. Results displayed heuristics as percentages of editing efficiency/risk. The
   summary now labels their heuristic status and reports scores out of 100.
4. An explanatory viewer opened first and fetched a public structure automatically.
   Results now open on Summary, with a separate 3D tab and explicit public-example
   loading. The viewer retry now starts a new load and PDB identifiers are bounded.
5. Progress treated any event as a completed stage, including failure events.
   Status derives from completion/failure evidence and actual run state. The UI
   uses the existing seven-stage backend vocabulary rather than the five-stage
   illustrative mockup. A stage with no completion evidence stays pending.
6. An unavailable backend previously made dashboard counts look like real zeros.
   Failed metrics now use an unavailable marker with a visible connection warning.
7. CI covered security scans but not the full application regression suite. Add
   backend lint/tests and frontend behavior/typecheck/lint/build jobs.
8. The JavaScript lockfile contained 38 high/critical dependency advisories.
   Refresh compatible dependencies, update Next.js and its lint packages to
   15.5.28, and override Next's older pinned PostCSS with 8.5.31. The refreshed
   graph resolves all three critical and 34 high advisories. One high advisory
   remains in build tooling: `braces <=3.0.3`,
   [GHSA-vfj7-8cjw-p6xm](https://github.com/advisories/GHSA-vfj7-8cjw-p6xm).
   Its upstream advisory lists no patched version. Keep it visible in the
   dedicated dependency CI job; do not suppress it or describe the audit as clean.
   Review build-time glob inputs and track upstream remediation before release.

Existing Supabase rows containing historical mock fields are not rewritten by
this change. Cleanup requires a separately reviewed data migration with known
targets. The new policy applies to newly created records.

## Follow-up review corrections (2026-10-22)

- Ignore `.casai-workspace/` at any depth, including raw uploads. This prevents
  accidental Git staging; it does not encrypt local data or replace access control.
- Bound guide mapping to 5,000 bases and 64 candidates. An exceeded ceiling
  returns `target_length_limit` or `candidate_count_limit`, no candidates and an
  empty ranking. Never rank a silently truncated subset. Narrow the supplied
  target/PAM and remap; genome-scale analysis requires a separate indexed engine.
  Persisted maps exceeding the candidate ceiling fail validation on reopen.
- Record unexpected adapter exceptions as sanitized failed-stage outcomes,
  preserving prior artifacts and required/optional-stage behavior. Interrupts
  are not swallowed; no fallback scientific result is invented.
- Put CORS outside transport middleware so 413/429 responses remain readable;
  exempt OPTIONS from rate budgets and expose `Retry-After`.
- Exempt only development `/docs`, `/redoc` and `/docs/oauth2-redirect` pages
  from API-only CSP. Other routes and production keep the restrictive policy;
  hosted interactive documentation is not enabled for production.
- Offload multipart FASTQ/VCF and reference parsing to worker threads after
  bounded upload reads; sequence/draft routes already use sync worker dispatch.
- Run push workflows only on `main`, retaining PR and manual triggers. The known
  unpatched `braces` advisory remains visible; no audit exception was introduced.
- Return explicit backend `stage_status` in provenance responses without a DB
  migration. Unknown/new events are visibly `unknown`, not inferred from suffixes;
  resolving an intent alone is running until schema validation completes.
- Fall back to exclusive `O_EXCL` creation when hard links are unsupported.
  Existing objects and concurrent winners are never overwritten. Unlike link
  publication, the fallback cannot guarantee atomic visibility or crash durability
  on every filesystem; partial objects fail integrity checks and need explicit
  recovery. Do not advertise all network/FAT filesystems as fully certified.
- Default to OS light/dark preference unless a valid user preference is saved;
  follow live OS changes until overridden. Storage denial still permits switching.
- Use the same tested no-file/invalid-file/reading guard on the Review button
  and submit handler. Removing the native file `required` attribute does not
  bypass validation, including when files are selected through drag/drop.

### Decisions required before production workflow/session persistence

`actor_id` is an unverified, client-supplied attribution label in this no-auth
demo. It MUST NOT authorize approval or separation of duties. Before exposing
those workflows, introduce a trusted server identity boundary and derive actors
from that context, not request JSON. Authentication is intentionally not added
in this correction.

Current v1 execution session/attempt IDs are deterministic, in-memory lineage
identifiers, not durable unique invocation IDs. Before persistence, version the
contract: retain deterministic plan/content IDs but assign a server-generated
unique session nonce per invocation and derive attempt IDs from session identity,
ordinal and retry parent. Scope any client idempotency key to the trusted actor
and submission. Repeating that key must reopen the same submission; a fresh
invocation must create a distinct session even for the same plan. Do not persist
the current v1 sessions as unique run records or silently reinterpret their IDs.

Future delivery work should use smaller focused PRs. This correction updates
the already requested consolidated PR without rewriting its history.

Review-correction validation: backend lint and all 577 tests pass; all 12
frontend behavior tests, TypeScript, ESLint and Next.js production build pass.
`git diff --check` passes. `bun audit --audit-level high` still reports the one
known unpatched advisory above. Filesystem fallback was tested with simulated
unsupported-link and concurrent-writer conditions, not physical FAT/network media.

## Validation for this increment

- `bun run lint:api`: passed.
- `bun run check:api`: passed, 537 tests (one upstream TestClient deprecation).
- `bun test apps/web/lib`: passed, eight tests.
- `bun run check:web`: typecheck, lint and production build passed.
- `bun run build`: monorepo production build passed against the final refreshed
  dependency graph (Next.js 15.5.28).
- `git diff --check`: passed; repeat before commit.
- Browser inspection: desktop light/dark toggle, persistence after reload and
  navigation, active Inputs navigation and 390px mobile intake without overflow.
  Backend-unavailable state verified; live Supabase writes and real scientific
  engines were not exercised in this local review.
- `bun audit --audit-level high`: one unresolved upstream high advisory above;
  this remains a release/review finding even when functional checks pass.

Reviewers should exercise a valid FASTA, a single-base target window, zero and
out-of-range coordinates, rapid file reselection, a failed run, theme reload and
navigation, and an unavailable backend. Confirm Summary opens before the 3D
example and that no structure download starts until explicitly requested.

## Next implementation sequence and acceptance criteria

### Local integration progress (2026-10-23; not full milestone completion)

Latest sequence handoff: confirmed records now support all-record normalized
FASTA download and explicit single-record run preparation. Migration 007 retains
the source version/record in legacy research objects; linked runs revalidate that
source and emit its identity in provenance. The older bullets below describe the
earlier increment. Deployment still requires migration 007 plus persistent shared
workspace storage; no live migration/deployment or production handoff rehearsal
has been performed. See desktop-demo.md for final checks and remaining limits.

- Implemented and locally tested the Information Processor panel with six draft
  methods, resume, warning/field-origin review and immutable confirmation.
  FASTQ/VCF text evidence inspection is connected separately. Multi-part/gzip,
  paired-file UI, durable hosted workspace storage and confirmed-version binding
  into legacy run preparation remain open.
- Added a v2 local execution revision journal with unique invocation/session and
  attempt identities, parent validation, retry/cancel history and integrity checks.
  It is backend-only, not a public approved-execution service or real engine run.
- Added a terminal-run JSON snapshot export, per-document checksums, client
  verification and scoped native Save As. Full originals/plan/scene/PDF packaging
  and enforceable rights/revocation records remain open; unknown rights do not
  grant commercial permission.
- Fixed the desktop public reference renderer and added the original interactive
  sequence schematic plus expandable reference popup. A manifest-driven mapped
  complex/trajectory viewer remains separate and unfinished.
- New backend endpoints require deployment; no pushes, deployments or remote CI
  dispatch are implied by local implementation. Real engine selection/reference
  licensing, trusted approval, cross-platform launch testing and release signing
  still require explicit configuration and external evidence.

### 1. Complete intake integration

Files: `apps/web/lib/api/client.ts`, `components/research-objects/`, intake routes,
workspace service and a new persistence adapter/migrations as needed.

- Connect the six declared input methods to stored draft and confirmation APIs.
- Display field origins, warnings, required/recommended gaps, molecule declaration,
  exact reference/version and explicit RNA conversion. Preserve FASTA records.
- Add FASTQ/VCF inspection UI as a separate evidence workflow; raw reads/variants
  must not masquerade as an executable target sequence.
- Connect confirmed versions to lists, run preparation and Supabase persistence.
  Keep the existing guided demo operational while migrating its legacy path.
- Live accession/gene resolution remains an explicit adapter with exact version,
  checksum and transcript selection. Never silently fetch or infer references.
- Verify upload/paste/demo, blocked confirmation, unresolved accession, ambiguous
  transcript, record preservation, immutable versions and resume-after-refresh.

### 2. Enzyme mapping and review approval

Files: new `modules/enzyme_mapping`, `modules/review`, schemas/routes and UI panels.

- Version constructs, sequences, domains, linkers, mutations, catalytic residues,
  chain/residue correspondence, missing coverage, geometry, units and uncertainty.
- Validate reference residues, reject ambiguous numbering/impossible geometry and
  retain separate sequence/structure/geometry/evidence score components.
- Add assigned work packets, dependencies, submission, changes requested,
  approval/rejection, comments and immutable decision history.
- Only submitted work may be reviewed; enforce separation of duties when enabled.
- Bind approved mappings and exact confirmed inputs to simulation-plan approval.
  Existing in-memory approval fields are not a substitute for a review record.
- Verify tampered IDs, self-approval policy, invalid state transitions, immutability
  and unavailable engine rejection before exposing executable-session endpoints.

### 3. Persisted execution and scientific adapter integration

Files: `modules/simulation/`, integration adapters, workspace/persistence layer,
simulation routes, `components/runs/`.

- Persist sessions, every attempt, exact engine/version and artifact outputs.
- Connect approved plans to explicit engine dispatch; retain cancellation and retry
  history across restarts. Never silently fall back to a heuristic engine.
- Preserve required-stage stop and optional-stage partial-result behavior.
- Demonstrate deterministic CBE and ABE paths using controlled fixtures and fake
  adapters in tests; real engines require installed runtimes and licensed references.

### 4. Manifest-driven molecular viewer

Files: `components/runs/simulation/`, typed scene API client and asset-serving routes.

- Render validated backend manifests and checksum-verified assets instead of
  treating a public example structure as the run's mapped enzyme/guide/target.
- Implement explicit residue/nucleotide selections, domain coloring, measurements,
  camera/visibility restoration, explanatory steps, before/after sequence views,
  screenshot export and manifest export.
- Keep experimental/predicted/explanatory labels and uncertainty visible. Only
  actual trajectory artifacts may be presented as simulation trajectories.
- Verify unsafe asset rejection and reproducible selections/camera state.

### 5. Export, data rights and reproducible packages

Files: new export/rights modules, schemas/routes, immutable artifact storage and UI.

- Build a manifest-driven bundle containing applicable originals, normalized and
  confirmed input, mappings, plan, results, evidence, warnings, provenance, scene,
  software/engine versions, PDF report and SHA-256 file checksums.
- Attach owner/license/classification/consent/permission/effective/revocation records
  to sources and derived artifacts. Unknown rights deny commercial reuse.
- Enforce rights when selecting artifacts, exporting or releasing a dataset.
  Revocation blocks future release without silently rewriting past versions.
- Verify byte/checksum completeness, safe filenames, no path traversal, no secret
  leakage and equivalent scientific payloads for equivalent immutable run versions.

### 6. Desktop product release: macOS, Windows and Linux

Files: `apps/desktop`, desktop workflows, shared API compatibility/connection UI.

- Replace the localhost packaging preview with a deliberately configured hosted
  UI or packaged client approach compatible with server-rendered Next.js routes.
- Define production origins/CSP and API compatibility before enabling runtime
  scripts/networking. Keep privileged credentials backend-only.
- Add native file selection, drag/drop, export-directory selection, version and
  connection/offline states, safe update notifications and validated deep links.
- Exercise product startup, input, run/result inspection and export on all three
  platforms. Signing/notarization/update publishing needs release credentials.

### 7. Release checks and later private-data security

- Add end-to-end CBE/ABE demo fixtures and a reproducible demo runbook.
- Reconcile old scaffold documentation with actual Supabase/local-store boundaries.
- Preserve backend-only secrets, bounded inputs, safe errors, restricted production
  CORS, scanning, backup/restore and incident response across new routes.
- Authentication/MFA, tenant isolation/RLS, roles, encrypted storage, expiring
  downloads, audit/retention/deletion, malware scanning, verified rights and an
  independent security review remain a separate private-data milestone.
- Keep invention notes and confidential engineering records in private storage;
  this public PR records no confidential invention details or legal conclusions.

## Shared UI basis

Use the approved Results schematic for every page: one 9rem desktop sidebar with
Workbench / Inputs / Runs, one content grid, navy serif page titles, sans-serif
controls, restrained emerald accents, thin borders and consistent card radii.
The same upper-right sun/moon control switches CSS tokens and persists locally.
Mobile navigation carries the same destinations and active state. Use actual API
data, honest offline/empty states and progressive disclosure of advanced details.
Mockup values and invented recommendations are not product data.

The historical B-number split is not fully recorded in the repository. Track the
capabilities and dependencies above as the authoritative remaining work rather
than inventing missing block titles. Previously excluded B3/B5/B8/B9/B10/B12 and
desktop/UI B11 work is now in Kavin's delivery scope.
