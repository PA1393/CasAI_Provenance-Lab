# Synthetic desktop rehearsal input

`synthetic-cbe.fasta` is a deliberately artificial 31-base software test string.
It is not a biological reference, patient sample or experimentally tested design.
It contains one 20-base guide followed by an NGG-compatible PAM, matching the
existing guide-mapping test pattern.

For an isolated deterministic engine check, use the guide
`AAACACAAAAAAAAAAAAAA`, CBE mode and guide positions 4–8 (1-based inclusive).
The known editable C positions in the forward target are 8 and 10. Verify this
with the existing engine/mapping tests; do not treat it as editing efficacy.

In the demo-review-1 client, choose **Use synthetic example** on Add input,
Review, then save without a PDB ID. Open Start Run, choose **Rule-based demo ·
C → T**, and enter a run label. The server uses its real deterministic guide
selection/edit/scoring pipeline without AI or retrieval. CBE changes positions
8 and 10, yielding `TTTTAAATATAAAAAAAAAAAAAAAGGTTTT`. ABE is available separately;
the label never controls its editor or biological objective. These modes need
the matching backend's `/api/v1/demo/capabilities` route and database access.

The separate **AI-assisted objective** mode still invokes configured AI/retrieval
services and may fail or resolve a different candidate. It does not silently
replace the selected rule-based path. Target-window annotations are metadata;
the current run pipeline searches the full supplied sequence. All demo runs are
limited to 5,000 bases. Review actual results and provenance, including failures.

`4UN3` is only a separately selected public viewer example. It does not describe
this artificial sequence or validate its interaction with an enzyme. Follow
`docs/desktop-demo.md` for deployment gates and the complete rehearsal.
