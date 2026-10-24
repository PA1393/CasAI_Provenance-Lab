import { test } from "node:test";
import assert from "node:assert/strict";
import { confirmationBody, validateTextInput, verifyConfirmedFasta, type ConfirmedFasta, type SequenceDraft } from "./intake";

const draft: SequenceDraft = { kind: "sequence", artifact_checksum: "source", normalized_checksum: "normalized", ready_for_confirmation: true, field_origins: {}, records: [], missing_fields: [], warnings: [{ code: "z", message: "review" }, { code: "a", message: "review" }] };
test("confirmation binds both checksums and sorted acknowledged warnings", () => {
  assert.deepEqual(confirmationBody(draft, " reviewer ", true), { expected_normalized_checksum: "normalized", expected_artifact_checksum: "source", actor_id: "reviewer", decision: "approve", acknowledged_warning_codes: ["a", "z"] });
  assert.throws(() => confirmationBody(draft, "reviewer", false));
  assert.throws(() => confirmationBody(draft, " ", true));
  assert.throws(() => confirmationBody({ ...draft, ready_for_confirmation: false }, "reviewer", true));
});
test("empty and over-budget input never submits", () => {
  assert.throws(() => validateTextInput("  "));
  assert.throws(() => validateTextInput("é".repeat(5_000_001)));
  assert.doesNotThrow(() => validateTextInput("ACGT"));
});

test("normalized FASTA download binds the exact version and bytes", async () => {
  const version = "sha256:" + "a".repeat(64);
  const content = `>record casai_version=${version}\nACGT\n`;
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(content));
  const value: ConfirmedFasta = { schema_version: "casai.confirmed-fasta.v1", version_id: version,
    filename: `casai-confirmed-${version.slice(7)}.fasta`, content,
    byte_length: new TextEncoder().encode(content).length,
    checksum: "sha256:" + Buffer.from(digest).toString("hex"), normalized_checksum: version,
    original_artifact_checksum: version, record_count: 1, claim_type: "explanatory", warning_codes: [] };
  await assert.doesNotReject(verifyConfirmedFasta(value, version));
  await assert.rejects(verifyConfirmedFasta({ ...value, filename: "../escape.fasta" }, version));
  await assert.rejects(verifyConfirmedFasta({ ...value, content: content.replace("ACGT", "AAAA") }, version));
  await assert.rejects(verifyConfirmedFasta(value, "sha256:" + "b".repeat(64)));
});
