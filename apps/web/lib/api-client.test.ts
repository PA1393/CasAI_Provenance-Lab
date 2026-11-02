import { afterEach, test } from "node:test";
import assert from "node:assert/strict";
import { createRun, getDemoCapabilities, getRunExport } from "./api/client";
import { ApiError, submissionMayExist } from "./api/errors";

const original = globalThis.fetch;
afterEach(() => { globalThis.fetch = original; });

test("run mode is explicit and both reads and writes have bounded credential-free requests", async () => {
  globalThis.fetch = (async (_, init) => {
    assert(init?.signal instanceof AbortSignal);
    assert.equal(init?.credentials, "omit");
    assert.equal(init?.redirect, "error");
    assert.equal(JSON.parse(init?.body as string).execution_mode, "demo_cbe");
    return Response.json({ run_id: "example" });
  }) as typeof fetch;
  await createRun({ research_object_id: "example", prompt: "Demo", execution_mode: "demo_cbe" });
});

test("interrupted submissions require inspection and never retry or expose server internals", async () => {
  let calls = 0;
  globalThis.fetch = (async () => { calls++; return new Response("private upstream detail", { status: 500 }); }) as typeof fetch;
  const error = await createRun({ research_object_id: "example", prompt: "Demo" }).catch(error => error);
  assert(error instanceof ApiError);
  assert.equal(submissionMayExist(error), true);
  assert(!error.message.includes("private"));
  assert.equal(calls, 1);
  globalThis.fetch = (async () => Response.json({}, { status: 422 })) as typeof fetch;
  assert.equal(submissionMayExist(await createRun({ research_object_id: "example", prompt: "Demo" }).catch(error => error)), false);
});

test("missing demo support and malformed export responses are visible errors", async () => {
  globalThis.fetch = (async () => Response.json({ schema_version: "older", run_execution_modes: [] })) as typeof fetch;
  assert.equal(await getDemoCapabilities(), false);
  globalThis.fetch = (async () => new Response("<html>not JSON</html>")) as typeof fetch;
  await assert.rejects(getRunExport("demo"), /unreadable response/);
});
