import assert from "node:assert/strict";
import { test } from "node:test";
import { parseTargetRegion } from "./target-region";

test("target coordinates retain inclusive endpoints, including a single base", () => {
  assert.deepEqual(parseTargetRegion("1", "10", 10), [1, 10]);
  assert.deepEqual(parseTargetRegion("5", "5", 10), [5, 5]);
  assert.equal(parseTargetRegion("", "", 10), undefined);
});

test("target coordinates reject zero, partial, fractional, inverted and out-of-range values", () => {
  for (const [start, end] of [["0", "3"], ["1", ""], ["", "3"], ["1.5", "3"], ["5", "4"], ["1", "11"]]) {
    assert.throws(() => parseTargetRegion(start, end, 10));
  }
});
