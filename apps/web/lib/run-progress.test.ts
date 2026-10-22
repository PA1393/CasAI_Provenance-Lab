import assert from "node:assert/strict";
import { test } from "node:test";
import { stageStatus } from "./run-progress";
import type { ProvenanceEvent } from "./api/client";

const event = (event_type: string, stage_status?: ProvenanceEvent["stage_status"]) => ({ event_type, stage_status } as ProvenanceEvent);

test("failed and informational events cannot be displayed as completed stages", () => {
  assert.equal(stageStatus("extract", [event("schema_invalid", "failed")], "extract", "failed"), "failed");
  assert.equal(stageStatus("input", [event("input_received", "pending")], "input", "queued"), "pending");
  assert.equal(stageStatus("score", [], "score", "failed"), "failed");
});

test("run progress distinguishes active work, completed evidence and terminal summary", () => {
  assert.equal(stageStatus("input", [event("input_validated", "completed")], "score", "running"), "completed");
  assert.equal(stageStatus("score", [], "score", "running"), "running");
  assert.equal(stageStatus("summary", [], "summary", "completed"), "completed");
  assert.equal(stageStatus("results", [], "score", "failed"), "pending");
});

test("backend status is authoritative and unknown events are not silently pending", () => {
  assert.equal(stageStatus("extract", [event("intent_resolved", "running")], null), "running");
  assert.equal(stageStatus("input", [event("new_event", "completed")], null), "completed");
  assert.equal(stageStatus("input", [event("pretend_validated", "unknown")], null), "unknown");
  assert.equal(stageStatus("input", [event("old_server_validated")], null), "unknown");
  assert.equal(stageStatus("input", [event("first", "completed"), event("second", "failed")], null), "failed");
});
