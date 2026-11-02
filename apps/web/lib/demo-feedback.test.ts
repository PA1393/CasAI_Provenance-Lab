import { test } from "node:test";
import assert from "node:assert/strict";
import { buildDemoFeedback } from "./demo-feedback";

test("feedback includes only explicit report fields and safe context, without input payloads", () => {
  const report = buildDemoFeedback({ category: "export", expected: " Save file ", actual: " File missing ",
    context: "/runs/demo-123", platform: "Demo OS", sequence: "must-not-export" } as Parameters<typeof buildDemoFeedback>[0]);
  assert.equal(report.expected, "Save file");
  assert.equal(report.context, "/runs/demo-123");
  assert(!JSON.stringify(report).includes("must-not-export"));
  assert.equal(buildDemoFeedback({ category: "other", expected: "", actual: "Test", context: "https://host/?secret=value", platform: "OS" }).context, "/");
});

test("empty, oversized and unknown feedback categories cannot be exported", () => {
  const input = { category: "run", expected: "", actual: "Test", context: "/", platform: "OS" };
  for (const changed of [{ actual: " " }, { actual: "x".repeat(2001) }, { expected: "x".repeat(2001) }, { category: "arbitrary" }]) {
    assert.throws(() => buildDemoFeedback({ ...input, ...changed }));
  }
});
