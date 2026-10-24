import assert from "node:assert/strict";
import { test } from "node:test";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { RunStatusBadge } from "../components/runs/run-status-badge";
import { RunPipeline } from "../components/runs/run-pipeline";
import { ReferenceStructurePanel } from "../components/runs/simulation/reference-structure-panel";
import { RunSummary } from "../components/runs/run-summary";
import type { Run } from "./api/client";

const run: Run = { run_id: "synthetic-run", research_object_id: "synthetic-input", prompt: "Synthetic test", created_at: "", started_at: null, completed_at: null, current_stage: "summary", guide_rna: null, status: "completed" };

test("overview badges are neutral without rewriting detailed failure status", () => {
  const overview = renderToStaticMarkup(createElement(RunStatusBadge, { status: "failed", overview: true }));
  assert(overview.includes("Review run"));
  assert(!overview.includes("text-accent-red"));
  assert(renderToStaticMarkup(createElement(RunStatusBadge, { status: "failed" })).includes("failed"));
});

test("provenance summary uses the completed run state, not an endless current-stage marker", () => {
  const html = renderToStaticMarkup(createElement(RunPipeline, { provenance: [], currentStage: "summary", runStatus: "completed" }));
  assert(html.includes("terminal summary state"));
  assert(!html.includes("CURRENT STAGE"));
});

test("reference panel is expandable and initially requests explicit public loading", () => {
  const html = renderToStaticMarkup(createElement(ReferenceStructurePanel, { phase: 0, pdbId: "4UN3" }));
  assert(html.includes("Expand molecular viewer"));
  assert(html.includes("Load public 3D example"));
  assert(!html.includes("Loading structure"));
});

test("completed run without stored results never invents a successful summary", () => {
  const html = renderToStaticMarkup(createElement(RunSummary, { results: [], run, onProvenance() {}, onInteraction() {} }, null));
  assert(html.includes("no result summary is stored"));
  assert(html.includes("not experimentally validated"));
});
