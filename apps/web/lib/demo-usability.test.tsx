import assert from "node:assert/strict";
import { test } from "node:test";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { parseWorkspaceConnection, connectionCopy } from "./connection-status";
import { exportNotice } from "./export-notice";
import { RunSummary } from "../components/runs/run-summary";
import { getWorkspaceConnection } from "./api/client";

const capabilities = { schema_version: "casai.demo-capabilities.v1", access_mode: "demo" };

test("connection state trusts explicit storage metadata, not a localhost guess", () => {
  const temporary = parseWorkspaceConnection({ ...capabilities, storage_backend: "temporary" }, "http://127.0.0.1:8815");
  assert.match(connectionCopy(temporary).label, /Temporary local demo/);
  assert.match(connectionCopy(temporary).detail, /Supabase is not used/);
  const localDatabase = parseWorkspaceConnection({ ...capabilities, storage_backend: "supabase" }, "http://localhost:8000");
  assert.equal(localDatabase.storage, "supabase");
  assert.match(connectionCopy(localDatabase).detail, /not verified/);
  assert(!connectionCopy(localDatabase).label.includes("Temporary"));
  assert.equal(parseWorkspaceConnection(capabilities, "http://[::1]:8000").location, "local");
  assert.equal(parseWorkspaceConnection(capabilities, "https://localhost.example.test").location, "hosted");
});

test("old or invalid contracts are rejected; missing or unfamiliar storage is unknown", () => {
  for (const value of [null, {}, { ...capabilities, schema_version: "old" }, { ...capabilities, access_mode: "private" }]) {
    assert.throws(() => parseWorkspaceConnection(value, "https://example.test"));
  }
  const status = parseWorkspaceConnection({ ...capabilities, storage_backend: "anything" }, "https://example.test/?secret=do-not-show");
  assert.equal(status.storage, "unknown");
  assert.match(connectionCopy(status).detail, /not been verified/);
  assert(!JSON.stringify(status).includes("secret"));
});

test("live connection retrieval parses public capabilities and rejects unreachable services", async () => {
  const original = globalThis.fetch;
  try {
    globalThis.fetch = (async url => {
      assert(String(url).endsWith("/api/v1/demo/capabilities"));
      return Response.json({ ...capabilities, storage_backend: "temporary" });
    }) as typeof fetch;
    assert.equal((await getWorkspaceConnection()).storage, "temporary");
    globalThis.fetch = (async () => { throw new TypeError("offline"); }) as typeof fetch;
    await assert.rejects(getWorkspaceConnection());
  } finally { globalThis.fetch = original; }
});

test("export messages never turn a browser request or cancellation into a confirmed save", () => {
  assert.match(exportNotice("requested"), /not a confirmed save/);
  assert.match(exportNotice("requested"), /fallback/);
  assert.match(exportNotice("saved"), /desktop app confirmed/);
  assert.match(exportNotice("cancelled"), /No file was written/);
  assert.match(exportNotice("requested", false), /too large/);
  assert(!exportNotice("requested", false).includes("fallback below"));
});

test("score guidance explains zero scores and bounded, PAM-agnostic off-target search", () => {
  const html = renderToStaticMarkup(createElement(RunSummary, { results: [], onProvenance() {}, onInteraction() {} }));
  for (const text of ["zero score does not mean", "40–60%", "1–3 mismatches", "excludes exact matches", "not a genome-wide safety assessment"]) assert(html.includes(text));
  assert(!html.includes("probability of success"));
});
