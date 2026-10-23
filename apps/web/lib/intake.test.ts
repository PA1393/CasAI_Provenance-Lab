import { test } from "node:test";
import assert from "node:assert/strict";
import { confirmationBody, validateTextInput, type SequenceDraft } from "./intake";

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
