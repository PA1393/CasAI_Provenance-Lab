import assert from "node:assert/strict";
import { test } from "node:test";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { failureStage, runFailure } from "./run-failure";
import { recordedRunSources } from "./run-sources";
import { RunFailurePanel } from "../components/runs/run-failure-panel";
import { RagSources } from "../components/runs/rag-sources";
import type { ProvenanceEvent, Run } from "./api/client";

const run = { status: "failed", current_stage: "extract", failure: {
  stage: "extract", code: "vault_no_evidence", message: "No relevant evidence matched.",
  next_step: "Refine the crop and gene objective.",
} } as Run;
test("run failure names the stage, explains why and gives the next step", () => {
  assert.equal(failureStage("extract", "vault_no_evidence"), "Vault search");
  assert.equal(failureStage("extract", "no_compatible_site"), "Guide selection");
  const html = renderToStaticMarkup(createElement(RunFailurePanel, { run }));
  assert(html.includes("Stopped during Vault search"));
  assert(html.includes("No relevant evidence matched."));
  assert(html.includes("Refine the crop and gene objective."));
});
test("historical missing reasons are not falsely attributed to a missing vault", () => {
  const issue = runFailure({ ...run, failure: null });
  assert.equal(issue?.code, "legacy_reason_unavailable");
  assert.match(issue!.next_step, /does not mean the vault lacked evidence/);
  assert.equal(runFailure({ ...run, status: "completed" }), null);
});
test("sources come from the actual analysis event, with safe URLs and finite scores", () => {
  const provenance = [{ stage: "extract", event_type: "intent_resolved", payload: { rag_sources: [
    { source_key: "ref", chunk_text: "recorded evidence", similarity: 0.8, source_url: "https://example.test/paper" },
    { source_key: "bad-url", chunk_text: "text", similarity: NaN, source_url: "javascript:alert(1)" },
    { source_key: 42, chunk_text: "invalid" },
  ] } }] as unknown as ProvenanceEvent[];
  const sources = recordedRunSources(provenance);
  assert.equal(sources.length, 2);
  assert.equal(sources[0].source_key, "ref");
  assert.equal(sources[1].source_url, null);
  assert.equal(sources[1].similarity, null);
});
test("rule-based runs explicitly say the vault was not used", () => {
  const provenance = [{ event_type: "input_validated", payload: { execution_mode: "demo_cbe" } }] as unknown as ProvenanceEvent[];
  const html = renderToStaticMarkup(createElement(RagSources, { sources: [], provenance, run: { ...run, status: "completed" } }));
  assert(html.includes("does not use the vault"));
  assert(!html.includes("No relevant evidence matched"));
});
