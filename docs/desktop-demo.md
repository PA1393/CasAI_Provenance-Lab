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
