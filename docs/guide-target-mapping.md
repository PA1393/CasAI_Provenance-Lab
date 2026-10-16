# Guide and target mapping

The `guide_mapping` module provides an offline, deterministic first layer for
reviewable CBE and ABE guide discovery. It does not call an LLM, external genome
service or scientific engine.

`GuideMappingRequest` requires an uppercase DNA/IUPAC target, source record ID,
editor, PAM, guide length, 1-based-inclusive edit window and optional exact
desired substitutions. Desired reference bases must match the supplied target.
Duplicate or out-of-range desired positions are rejected.

`map_guides(...)` enumerates both target orientations. A candidate is emitted
only when:

- the complete protospacer and PAM fit inside the target;
- the PAM matches the declared IUPAC pattern immediately 3-prime of the oriented
  protospacer;
- the protospacer contains only unambiguous A/C/G/T bases; and
- at least one editor-compatible base is inside the declared window.

All target, protospacer, PAM and edit coordinates are reported against the
original forward target using 1-based-inclusive coordinates. Reverse-strand CBE
is represented as G-to-A on the forward target; reverse-strand ABE is represented
as T-to-C. Each candidate separates requested edits from bystander edits and
states whether it covers every requested position. Incompatible desired changes,
unmapped desired positions and absence of a compatible guide remain explicit
issues.

Guide candidates and complete maps are immutable, content-addressed contracts.
They remain `status=draft`, `executable=false` and `claim_type=heuristic`.

`rank_guides(...)` adds a separate content-addressed heuristic ranking. It keeps
desired-edit coverage, bystander avoidance, edit-window centrality, guide
composition and within-target specificity as individually labeled components.
Candidates are ordered lexicographically by those declared components; no opaque
aggregate score is emitted. The local specificity component is PAM-agnostic and
is explicitly not a genome-wide off-target search. The guide-composition
component is not a trained efficacy model or experimental measurement.

Mapping and ranking do not claim guide optimality, genome-wide specificity,
biological effect, allele selectivity, delivery feasibility, safety or
experimental validation. External off-target adapters, approval/versioning and
API exposure belong to later reviewable increments.

Run the focused tests from `apps/api`:

```bash
python -m pytest -q tests/test_guide_mapping.py
```
