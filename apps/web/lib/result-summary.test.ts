import { describe, test } from "node:test";
import assert from "node:assert/strict";
import { heuristicScore, summarizeResults } from "./result-summary";
import type { Result } from "./api/client";

const record: Result = {
  result_id: "synthetic-result", run_id: "synthetic-run", research_object_id: null,
  edited_sequence: null, edit_summary: null, off_target_score: 0.2,
  on_target_score: 0.8, notes: null, reproducible: false,
};

describe("result summary without invented scientific evidence", () => {
  test("formats normalized heuristics, including real zero, not percentages", () => {
    assert.equal(heuristicScore(0), "0 / 100");
    assert.equal(heuristicScore(1), "100 / 100");
    assert.equal(heuristicScore(0.812), "81 / 100");
  });
  test("leaves missing, nonfinite and out-of-contract scores absent", () => {
    for (const value of [null, undefined, NaN, Infinity, -0.1, 1.1]) assert.equal(heuristicScore(value), "—");
  });
  test("does not select the best result or reorder backend records", () => {
    const rows = [record, { ...record, result_id: "second", on_target_score: 0.99 }];
    assert.deepEqual(summarizeResults(rows), { onTarget: "80 / 100", offTarget: "20 / 100", count: 2 });
    assert.equal(rows[0], record);
  });
  test("handles empty results without an invented zero score", () => {
    assert.deepEqual(summarizeResults([]), { onTarget: "—", offTarget: "—", count: 0 });
  });
});
