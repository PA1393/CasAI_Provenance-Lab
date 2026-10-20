import assert from "node:assert/strict";
import { test } from "node:test";
import { stageStatus } from "./run-progress";
import type { ProvenanceEvent } from "./api/client";

const event = (event_type: string) => ({ event_type } as ProvenanceEvent);

test("failed and informational events cannot be displayed as completed stages", () => {
  assert.equal(stageStatus("extract", [event("schema_invalid")], "extract", "failed"), "failed");
  assert.equal(stageStatus("input", [event("input_received")], "input", "queued"), "pending");
  assert.equal(stageStatus("score", [], "score", "failed"), "failed");
});

test("run progress distinguishes active work, completed evidence and terminal summary", () => {
  assert.equal(stageStatus("input", [event("input_validated")], "score", "running"), "completed");
  assert.equal(stageStatus("score", [], "score", "running"), "running");
  assert.equal(stageStatus("summary", [], "summary", "completed"), "completed");
  assert.equal(stageStatus("results", [], "score", "failed"), "pending");
});
