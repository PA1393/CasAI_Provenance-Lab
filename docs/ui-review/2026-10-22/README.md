# Pre-push UI review — 2026-10-22

These AI-generated design proposals use one visual system across three screens,
each in light and dark mode. Generated with the built-in image tool; the exact
prompt set is in `prompts.txt`. They are NOT screenshots, implementation evidence,
scientific structures, or proof of a working hosted demo. No new alternative
layout is selected or implemented by adding these files.

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
  and deployment limitations in `../../desktop-demo.md` (from the docs root).
- Confirm the hosted API is updated before permitting new demo submissions.
- Windows/Linux packaging and clean-machine interactive launches remain release
  gates; local Mac launch does not prove all-platform readiness.

This review bundle and the desktop implementation are local-only until an
explicit push is authorized. No remote branch, PR or deployment is changed by
this review step.
