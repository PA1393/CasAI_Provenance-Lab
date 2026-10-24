import { test } from "node:test";
import assert from "node:assert/strict";
import { verifyDemoExport, type DemoExport } from "./demo-export";

async function fixture(): Promise<DemoExport> {
  const content = "{}";
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(content));
  const sha256 = Buffer.from(digest).toString("hex");
  return { schema_version: "casai.demo-export.v1", run_id: "test", limitations: [], files: ["input.json", "results.json", "run.json", "provenance.json"].map(path => ({ path, content, sha256, encoding: "utf-8", byte_length: 2 })) };
}
test("verifies every exported byte and rejects tampering", async () => {
  const value = await fixture();
  assert.match(await verifyDemoExport(value, "test"), /casai.demo-export.v1/);
  value.files[0].content = "[]";
  await assert.rejects(verifyDemoExport(value, "test"), /integrity/);
});
test("rejects foreign runs, path traversal and duplicate/missing files", async () => {
  const value = await fixture();
  await assert.rejects(verifyDemoExport(value, "other"));
  value.files[0].path = "../secret";
  await assert.rejects(verifyDemoExport(value, "test"));
  value.files[0].path = "run.json";
  await assert.rejects(verifyDemoExport(value, "test"));
});
