import assert from "node:assert/strict";
import { describe, test } from "node:test";

import { canReviewUpload, inspectFastaUpload, MAX_UPLOAD_BYTES } from "./fasta-review";

test("review cannot advance without a file or while file validation is incomplete", () => {
  const file = { name: "target.fa" };
  const ready = inspectFastaUpload(file.name, 13, ">target\nACGT\n");
  const empty = inspectFastaUpload(file.name, 0, "");
  assert.equal(canReviewUpload(null, null, false), false);
  assert.equal(canReviewUpload(null, ready, false), false);
  assert.equal(canReviewUpload(file, null, false), false);
  assert.equal(canReviewUpload(file, ready, true), false);
  assert.equal(canReviewUpload(file, empty, false), false);
  assert.equal(canReviewUpload(file, ready, false), true);
});

describe("inspectFastaUpload", () => {
  test("normalizes RNA and reports review facts", () => {
    const review = inspectFastaUpload("target.fna", 24, ">target\nAUGCRN\n");

    assert.equal(review.ready, true);
    assert.equal(review.sequence, "ATGCRN");
    assert.equal(review.sequenceLength, 6);
    assert.equal(review.recordCount, 1);
    assert.equal(review.gcContent, 0.5);
    assert.equal(review.ambiguousBases, 2);
  });

  test("rejects unsupported extensions and invalid bases", () => {
    const review = inspectFastaUpload("target.fastq", 12, ">target\nACGTZ");

    assert.equal(review.ready, false);
    assert.deepEqual(review.issues.map((issue) => issue.message), [
      "This intake currently accepts .fasta, .fa, and .fna files.",
      "Invalid sequence characters: Z.",
    ]);
  });

  test("rejects files over the backend limit", () => {
    const review = inspectFastaUpload("target.fa", MAX_UPLOAD_BYTES + 1, ">target\nACGT");

    assert.equal(review.ready, false);
    assert.match(review.issues[0]?.message ?? "", /10 MB limit/);
  });

  test("warns when multiple records will be concatenated", () => {
    const review = inspectFastaUpload("targets.fasta", 32, ">one\nACGT\n>two\nTGCA");

    assert.equal(review.ready, true);
    assert.equal(review.recordCount, 2);
    assert.equal(review.sequence, "ACGTTGCA");
    assert.equal(review.issues[0]?.severity, "warning");
  });
});
