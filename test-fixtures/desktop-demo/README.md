# Synthetic desktop rehearsal input

`synthetic-cbe.fasta` is a deliberately artificial 31-base software test string.
It is not a biological reference, patient sample or experimentally tested design.
It contains one 20-base guide followed by an NGG-compatible PAM, matching the
existing guide-mapping test pattern.

For an isolated deterministic engine check, use the guide
`AAACACAAAAAAAAAAAAAA`, CBE mode and guide positions 4–8 (1-based inclusive).
The known editable C positions in the forward target are 8 and 10. Verify this
with the existing engine/mapping tests; do not treat it as editing efficacy.

An example UI prompt is: “Synthetic software test only: use a CBE C-to-T edit
with guide AAACACAAAAAAAAAAAAAA and PAM NGG.” The current run flow may invoke
the hosted LLM/retrieval services, so model interpretation is not guaranteed by
this fixture. Check the actual output/provenance and report failures honestly.

`4UN3` is only a separately selected public viewer example. It does not describe
this artificial sequence or validate its interaction with an enzyme. Follow
`docs/desktop-demo.md` for deployment gates and the complete rehearsal.
