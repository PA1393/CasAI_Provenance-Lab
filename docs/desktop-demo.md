# Desktop demo: build, launch and rehearsal

This is an internet-connected concept demo, not an offline scientific simulator
or a signed public release. The UI is embedded in a Tauri executable; users do
not need Node, Bun, Python or a local web server to launch a built package.

## Architecture and security boundary

- `apps/desktop` builds a static React client with Vite. It reuses the existing
  web view functions, components, theme and API types. Tiny desktop adapters
  replace only Next link/navigation/lazy-loading; no Next server is bundled.
- The native `api_request` command reaches only
  `https://casaiprovenancelab.vercel.app` and explicitly permitted GET/POST paths.
  Requests/responses are bounded, timed out and never retried automatically.
  Redirects, arbitrary hosts, headers, cookies, filesystem and shell access are
  not exposed. Supabase/OpenAI service credentials stay on the hosted backend.
- Normal installed API requests use this native bridge, so the website's CORS
  policy does not need to be broadened. Browser-only previews still obey CORS.
- Top-level navigation stays on the app origin. CSP permits local scripts and
  explicit API/public-PDB connections. The optional public molecular viewer
  loads from RCSB only after the user's click; it remains explanatory.
- Health plus the required OpenAPI route inventory are checked at startup.
  Missing merged intake/mapping/planning endpoints visibly mark the backend
  outdated and block UI submissions. This is a compatibility gate, not an
  authentication boundary or scientific accuracy certificate.

## Build prerequisites (developers only)

Install Bun, Rust stable (including rustfmt), and Tauri's platform prerequisites:
<https://v2.tauri.app/start/prerequisites/>. macOS requires Xcode tools;
Windows requires the supported MSVC/WebView2 environment; Linux requires WebKitGTK.

From the repository root:

```sh
bun install --frozen-lockfile
bun run check:desktop
cargo test --locked --manifest-path apps/desktop/src-tauri/Cargo.toml
bun run build:desktop
```

The default bundling command builds that host's supported packages. For a Mac
app only: `bun run --cwd apps/desktop package --bundles app`. Artifacts are under
`apps/desktop/src-tauri/target/release/bundle/`. Never commit generated targets.

`bun run dev:desktop` starts the desktop development UI on port 1420. Development
previews are not proof the release works: rehearse the packaged `.app`/installer
with no Next or Vite dev server running.

## Installers and distribution

The Desktop package smoke workflow builds macOS `.app`, Windows NSIS installer
and Linux DEB/AppImage artifacts. It runs native boundary tests before packaging,
has read-only repository permissions, and does not publish a GitHub Release.
Run it manually on `KavNewPR` when reviewing desktop changes after the prior PR
has merged. Download artifacts from the workflow's artifact section.

The Mac default uses an ad-hoc signature for local/internal testing, not an
Apple Developer ID or notarization. Windows is not publisher-signed. Do not
disable OS security protections. Public redistribution requires proper signing,
notarization where applicable, and clean-machine launch tests. Build success on
another OS is not a claim its installer has passed interactive launch testing.

## Backend deployment readiness

The API deployment must actually build the merged backend, not just rebuild the
Next frontend. Confirm its deployed commit, project root and any API rewrites.
Keep Supabase/OpenAI credentials server-side, use HTTPS and restricted demo
access, and use only synthetic/public data in this no-auth concept phase.

Check `/health` returns `{"status":"ok"}` and `/openapi.json` includes:

- `/api/v1/intake/research-drafts`
- `/api/v1/guide-maps`
- `/api/v1/simulation-plans`

Presence of these routes is a basic version check only. A fresh synthetic upload
must also leave unmeasured QC/structure fields null. Historical mocked database
rows are not rewritten; never present their values as experimental measurements.
The legacy run flow needs the deployed backend's Supabase schema and configured
LLM/retrieval dependencies. Missing dependencies must fail visibly, not invent a
successful result. Local intake workspace persistence is a separate boundary;
serverless deployments need durable storage before using it for real work.

## Rehearsal with a synthetic input

1. Open the packaged app. Check it renders without any local dev server.
2. Check the connection banner. If outdated/unavailable, stop server submissions
   and fix the deployment, then Refresh. Do not work around the compatibility gate.
3. Switch light/dark mode, navigate and relaunch to verify the saved theme.
4. Add `test-fixtures/desktop-demo/synthetic-cbe.fasta`. With no file, Review must
   be disabled. The selected sample must show 31 bp, one record and zero ambiguity.
5. Name it `Synthetic desktop smoke — <date>`; enter `4UN3` as a separately labeled
   public example, not a structure matched to this synthetic sequence. Review,
   then explicitly create the record. Check its identity and sequence length.
6. Only after backend readiness passes, start a CBE concept run with an explicit
   synthetic-edit prompt. This may consume the backend's configured LLM service.
   The fixture README describes the deterministic engine check; LLM intent
   extraction and deployment availability are separate failure points.
7. Confirm the actual terminal run status, results and provenance. On a timeout,
   inspect Runs before resubmitting; an interrupted client response does not prove
   the server rolled back the request. Never retry a POST automatically.
8. Open 3D interaction, explicitly load the public example and verify rendering/
   rotation. State clearly that the public structure and phase animation are not
   a mapped enzyme trajectory or validated interaction prediction.
9. Test disconnected behavior, reconnection, relaunch and the same workflow on
   Windows/Linux clean machines before calling the three-platform demo ready.

## Verification and remaining release gates

On 2026-10-22 the local Mac release bundle built and passed `codesign --verify`.
Native UI inspection verified launch, live API reads, FASTA selection, local
review and one explicitly labeled synthetic-record submission. No existing
records were edited or deleted. That submission exposed an old deployed API:
the new record contained unmeasured QC/retrieval fields, and its OpenAPI inventory
still had only 10 paths. New live runs were therefore stopped, and the client
now blocks submissions against that outdated inventory.

Full latest-backend upload/run/results/3D rehearsal remains a deployment gate,
not a completed test. Platform packaging outcomes and native launch evidence
must be reported separately. The existing `braces` advisory remains unsuppressed;
passing functional tests does not make the dependency audit clean.

## Approved layout integration (2026-10-22)

The shared web/desktop views now implement the approved layout family: compact
workbench steps, upload/checklist intake, and result cards/table with a run-record
rail. Both themes use the same components. The results table preserves backend
order, never claims ranking, and leaves invalid/missing scores absent.
View provenance was verified in the packaged Mac app to select and focus the
Provenance tab for an existing run. Native inspection also verified light/dark
switching, the new intake checklist, and disabled Review with no selected file.
These were read-only checks against historical demo records, not a fresh
latest-backend run or evidence of scientific validity. No new submissions were
made during this layout verification.

Pre-push layout checks: 577 backend tests and backend lint, 16 web behavior
tests, web TypeScript/ESLint/production build, 12 desktop tests and desktop
TypeScript/Vite build passed. The Mac package rebuilt and its ad-hoc signature
verified. The three native boundary tests passed for the desktop increment;
native Rust source is unchanged by this layout change. The dependency audit
still reports the known high-severity braces advisory; it is not audit-clean.

## Molecular-viewer correction and original CasAI scene

The original published desktop build could fail while evaluating Mol*/Immutable
namespace and prototype methods under Tauri's frozen Object.prototype. The
desktop build now transforms those vetted dependency assignments into compatible
own-property definitions. The global prototype freeze, CSP and native request
boundaries remain enabled. The transform also runs during dependency optimization;
tests cover actual installed library source, assignment values and frozen globals.

The public viewer has a panel-local error boundary, initialization/representation
checks and a diagnostic/retry path. It supports an expanded native HTML dialog,
Escape/Close, return focus, camera reset, protein and nucleic-acid visibility,
optional camera rotation and opt-in illustrative phase styling. Neither rotation
nor colors are a calculated molecular trajectory, and deposited coordinates are
not edited to claim a predicted base conversion.

CasAI's original sequence explorer renders a bounded 64-base window using its
own 3D schematic geometry and perspective projection. Orbit, zoom, keyboard
camera controls, base selection, windowing and reset operate on the actual
supplied sequence. Changed bases are identified by comparison to a same-length
stored output; missing/mismatched output never invents an edit. This is NOT an
atomic model, force field, docking engine, enzyme pathway or molecular dynamics.

The run Summary displays the persisted deterministic edit summary. Provenance
receives run status so a completed terminal summary is not shown as perpetually
active. No new AI-generated biological interpretation is introduced. Overview
failure badges become neutral Review run links; run-detail status and the audit
trail still disclose failures. No historical records are rewritten.

Public reference examples were checked against the source catalog:
[4UN3](https://www.rcsb.org/structure/4UN3),
[5F9R](https://www.rcsb.org/structure/5F9R) and
[6VPC](https://www.rcsb.org/structure/6VPC). These are separate references, not
structures matched or validated against the user's sequence.

This correction does not complete all B-blocks; the follow-up below adds intake,
export and local execution-journal plumbing without claiming full delivery.

## Demo integration follow-up (2026-10-23)

The Add input screen now includes an Information Processor alongside the legacy
guided FASTA form. It connects the six existing input methods to stored-draft,
summary/resume and immutable-confirmation APIs. It displays record identities,
checksums, field origins, warnings and missing-field actions, and requires review
acknowledgment plus a non-authenticated attribution label. Only a draft ID is
saved in browser preferences; sequence payloads are not placed in localStorage.
Protein/RNA declarations and explicit RNA-to-DNA conversion remain distinct.
Accession, gene and objective requests stay non-executable when unresolved;
no automatic biological reference downloads or invented sequence are added.

FASTQ/VCF evidence uses a new bounded JSON text-inspection endpoint compatible
with the scoped native transport. Inputs are uncompressed UTF-8; the existing
multipart API remains the path for gzip and paired files, which this UI does not
yet expose. Phred+33 requires an explicit user declaration. VCF can optionally
receive a supplied reference for REF checking. Evidence inspection returns
metadata only, does not persist those datasets, and cannot launch sequence runs.
Confirmed workspace versions are not yet bridged into the legacy Supabase run
workflow. Hosted serverless workspace persistence is still a deployment concern.

Terminal runs have Export recorded data above the tabs. The API builds an
allowlisted JSON snapshot containing input, run, results and provenance documents,
their exact UTF-8 byte lengths and SHA-256 digests. The client verifies every file
before requesting a download. The packaged client opens native Save As and uses
exclusive creation, never a JavaScript-supplied absolute path or an overwrite.
Cancellation writes nothing. This is NOT a complete immutable archive, PDF report,
source-rights verification or commercial reuse license. Originals, approved plans,
mapped scene assets and trajectory artifacts are explicitly absent. Historical
demo data may include old placeholders; checksum validation is not scientific validation.
Exports require the new backend route to be deployed before use; no deployment
or live export was performed in this increment. Local API/byte-integrity tests
passed; native Save As has compiled but has not completed an end-to-end save test.

`simulation/durable.py` adds a v2 backend-only local execution journal. A fresh
server nonce distinguishes invocations, attempts bind to session/retry identity,
and immutable checksummed revisions preserve outcomes/cancellation across reopen.
Transitions validate their stored parent. V1 identity semantics are unchanged.
There is no mutable latest pointer, distributed job scheduler, public executable
session route or actor-scoped idempotency implementation. Caller attribution is
not authority. Trusted approval, approved mapping integration and installed real
scientific engines must precede exposing executable sessions.

Native macOS inspection verified deposited 4UN3 rendering (13,629 structure
elements), expanded popup, protein visibility, reset camera and Escape/focus return.
The renderer now flushes deferred canvas commits before checking readiness;
otherwise WKWebView can falsely report an empty representation while its
animation loop has not committed. A final package rebuild includes the new UI.
Screen evidence was displayed inline; saving a screenshot file was blocked by
the UI tool's filesystem restrictions, and no video recording tool was available.

Validation: backend lint and 587 tests; 28 web behavior tests; 16 desktop tests;
web/desktop typecheck and builds; four native Rust tests. Repeat final builds
after changes. Windows/Linux packaging and interactive launch checks for this
increment have not run; the matrix remains configured but no CI was dispatched.
macOS ad-hoc packaging is not public signing/notarization. The known braces
advisory is not suppressed. See remaining-delivery-plan.md for unfinished work.
