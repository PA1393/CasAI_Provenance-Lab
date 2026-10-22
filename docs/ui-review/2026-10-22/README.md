# Pre-push UI review — 2026-10-22

These AI-generated design proposals use one visual system across three screens,
each in light and dark mode. Generated with the built-in image tool; the exact
prompt set is in `prompts.txt`. They are NOT screenshots, implementation evidence,
scientific structures, or proof of a working hosted demo. The user subsequently
approved implementing this layout family; see implementation status below.

## Implemented after approval

- Workbench: short product copy, three-column intake steps, existing-input/run
  cards and actual data counts, with unavailable data kept distinct from zero.
- Intake: three-step progress strip, upload/checklist columns, selected-file
  summary and Remove action, Cancel and Review input controls. Existing file,
  coordinate and required-detail validation remains in force. No file means no
  advance to Review. FASTA only; no implied FASTQ/VCF UI support.
- Results: three summary cards, recorded-designs table and Run record rail.
  View provenance selects/focuses the existing Provenance tab. Open 3D tab selects
  the explanatory viewer without automatically downloading a structure.
- Scientific corrections to the concept board: rows are in backend order, NOT
  ranked/recommended; design count is NOT a passing-filter count. Summary scores
  are explicitly from the first stored result, not the best design. Missing or
  invalid scores show a dash, never a fabricated zero or efficacy percentage.
- Method version is not supplied by this API and is not invented. Actual input
  hash, run ID, completion timestamp and run status populate the record rail.
  Failed results/provenance requests display warnings rather than empty success.
- Detailed sequences/notes and processing/timing details remain accessible in
  disclosure panels. Existing backend records are unchanged.

The board notes below describe the original proposals and their differences
from the pre-implementation UI. Actual components, not generated pixels, are
the source of truth for the approved implementation.

## Shared reference and current implementation

The reference is the user-provided Results image: narrow left navigation,
CasAI serif wordmark and large serif headings, navy text, emerald actions, mint
selection states, quiet borders and white cards. The code already shares
`SiteShell`, `Sidebar`, `Header`, `Navigation`, and `ThemeToggle` between views.
`apps/web/app/globals.css` defines corresponding light/dark tokens. The desktop
client reuses these components, rather than maintaining a different product UI.
OS theme preference is respected until a valid saved preference overrides it.

The implementation is not a pixel-perfect reproduction of the reference. The
current Results content is per-result detail, not the proposed candidate-table
and run-record grid; it includes Sources alongside Summary, 3D interaction and
Provenance. The original image's Export package action is not a verified feature
of this UI and is deliberately omitted from these proposals.

## Review boards

- [A — Guided workbench](a-workbench.png): two primary cards, compact workflow,
  counts and recent work. Closest to the existing workbench, but the compact
  spacing and reworked step visualization remain proposals.
- [B — Focused intake](b-intake.png): upload-first main column and checklist.
  The side checklist and this exact composition are proposals. Existing intake
  already supports FASTA selection, local preview, details and review guards.
  FASTQ/VCF backend parsing is NOT wired into this main form.
- [C — Results workspace](c-results.png): summary cards and candidate table with
  a run-record rail. This grid/table is proposed, not implemented. Public 3D
  structures remain click-to-load in their separate tab, not automatically loaded
  by a real Summary page. The illustrated protein is generated artwork, not a
  verified molecular structure.

All board values/statuses are illustrative. In particular, B's Connected badge
does not report deployment readiness; C's Completed badge is a mock state even
though result values are absent. Actual statuses must follow backend evidence.

## Review before choosing a layout or pushing

- Confirm A/B/C should be complementary screens of one product, not alternatives
  with divergent navigation or themes.
- Select any proposed layout refinements before changing production views.
- Rehearse keyboard focus, no-file/invalid-file guards, loading/error/empty states,
  theme persistence, small windows, and the actual packaged app.
- Keep unavailable measurements absent; label scores as heuristics. Do not claim
  a public structure is mapped to the input or an enzyme trajectory is simulated.
- Review the desktop transport, compatibility gate, packaging workflow, fixture
  and deployment limitations in [desktop-demo.md](../../desktop-demo.md).
- Confirm the hosted API is updated before permitting new demo submissions.
- Windows/Linux packaging and clean-machine interactive launches remain release
  gates; local Mac launch does not prove all-platform readiness.

The user has now authorized committing and pushing the approved layout and
previous desktop work to KavNewPR. This does not authorize merging or deploying.
