import assert from "node:assert/strict";
import { test } from "node:test";
import { complementBase, initialSceneStart, MAX_SCENE_BASES, sequenceScene } from "./scene-geometry";

test("scene is bounded and preserves exact reference coordinates", () => {
  const rows = sequenceScene("A".repeat(1000), null, 101, 110);
  assert.equal(rows.length, MAX_SCENE_BASES);
  assert.equal(rows[0].position, 101);
  assert.equal(rows[63].position, 164);
  assert.equal(rows.filter(base => base.guide).length, 20);
  assert(rows.every(base => [base.x, base.y, base.z].every(Number.isFinite)));
});

test("scene never invents edits or substitutes a mismatched output", () => {
  assert.equal(sequenceScene("", "A", 1).length, 0);
  assert(sequenceScene("ACGT", "TT", 1).every(base => base.output === null && !base.changed));
  const rows = sequenceScene("ACGT", "ATGT", 1);
  assert.deepEqual(rows.filter(base => base.changed).map(base => base.position), [2]);
  assert.equal(rows[1].reference, "C");
  assert.equal(rows[1].output, "T");
});

test("scene clamps invalid windows and never infers an invalid guide span", () => {
  assert.equal(sequenceScene("ACGT", null, NaN, Infinity)[0].position, 1);
  assert.equal(sequenceScene("ACGT", null, 999)[0].position, 4);
  assert.equal(sequenceScene("ACGT", null, -4)[0].position, 1);
  assert(sequenceScene("A".repeat(40), null, 1, 30).every(base => !base.guide));
  assert.equal(initialSceneStart(31, 2), 1);
  assert.equal(initialSceneStart(1000, 900), 884);
});

test("complement labels handle unknown bases without pretending they are known", () => {
  assert.equal(complementBase("A"), "T");
  assert.equal(complementBase("C"), "G");
  assert.equal(complementBase("N"), "N");
});
