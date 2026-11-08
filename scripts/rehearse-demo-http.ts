// Integration rehearsal ONLY against a deliberately marked disposable loopback fixture.
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { verifyDemoExport } from "../apps/web/lib/demo-export";

const base = process.argv[2];
const target = new URL(base);
if (process.argv[3] !== "--write-disposable-demo-data" || target.protocol !== "http:" ||
    !["127.0.0.1", "localhost"].includes(target.hostname) || target.pathname !== "/" ||
    target.username || target.password || target.search || target.hash) {
  throw new Error("Requires an explicit disposable loopback API and --write-disposable-demo-data. Never run against hosted research data.");
}
async function request(path: string, body?: object) {
  const response = await fetch(base.replace(/\/$/, "") + path, body ? {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
    signal: AbortSignal.timeout(15_000),
  } : { signal: AbortSignal.timeout(15_000) });
  assert(response.ok, `${path}: HTTP ${response.status}`);
  return response.json();
}
const marker = await request("/__disposable_rehearsal__");
assert.equal(marker.disposable, true);
assert.equal(marker.hosted_writes, false);
assert.equal((await request("/api/v1/demo/capabilities")).access_mode, "demo");
const before = await request("/api/v1/runs/metrics");
const fasta = await readFile(new URL("../test-fixtures/desktop-demo/synthetic-cbe.fasta", import.meta.url), "utf8");
async function input(name: string, text?: string) {
  return request("/api/v1/research-objects", {
    name, input_filename: "synthetic.fasta", input_file_type: "fasta", pdb_id: "",
    ...(text ? { fasta_text: text } : {}),
  });
}
const valid = await input("Disposable synthetic review", fasta);
const noPam = await input("Disposable no-PAM review", ">synthetic_no_pam\n" + "AT".repeat(20) + "\n");
const noSequence = await input("Disposable absent-sequence review");
const cbe = await request("/api/v1/runs", { research_object_id: valid.research_object_id, prompt: "CBE fixture", execution_mode: "demo_cbe" });
const abe = await request("/api/v1/runs", { research_object_id: valid.research_object_id, prompt: "ABE fixture", execution_mode: "demo_abe" });
assert.equal(cbe.status, "completed");
assert.equal(abe.status, "completed");
for (const [source, mode, expected] of [
  [noPam, "demo_cbe", "no_compatible_site"],
  [valid, "assisted", "vault_not_configured"],
  [noSequence, "assisted", "input_invalid"],
] as const) {
  const run = await request("/api/v1/runs", { research_object_id: source.research_object_id, prompt: "Deliberate dependency/input test", execution_mode: mode });
  assert.equal(run.status, "failed");
  assert.equal(run.failure.code, expected);
  assert(run.failure.stage && run.failure.message && run.failure.next_step);
  assert.equal((await request(`/api/v1/runs/${run.run_id}/results`)).items.length, 0);
  const exported = await request(`/api/v1/runs/${run.run_id}/export`);
  await verifyDemoExport(exported, run.run_id);
  assert.equal(JSON.parse(exported.files.find((file: {path:string}) => file.path === "run.json").content).failure.code, expected);
}
const folder = await request("/api/v1/folders", { name: "Disposable rehearsal folder" });
for (const [kind, record_id] of [["input", valid.research_object_id], ["run", cbe.run_id]]) {
  await request("/api/v1/folders/place", { kind, record_id, folder_id: folder.folder_id });
}
assert.equal((await request(`/api/v1/research-objects/${valid.research_object_id}`)).folder_id, folder.folder_id);
assert.equal((await request(`/api/v1/runs/${cbe.run_id}`)).folder_id, folder.folder_id);
const exported = await request(`/api/v1/runs/${cbe.run_id}/export`);
await verifyDemoExport(exported, cbe.run_id);
const result = JSON.parse(exported.files.find((file: {path:string}) => file.path === "results.json").content)[0];
assert.match(result.edit_summary, /8, 10/);
// Exercise the actual processor -> immutable confirmation -> run-input handoff.
const stored = await request("/api/v1/intake/research-drafts", { input_method: "fasta", molecule_type: "DNA", content: fasta });
const confirmed = await request(`/api/v1/intake/research-drafts/${stored.draft_id}/confirm`, {
  expected_normalized_checksum: stored.draft.normalized_checksum,
  expected_artifact_checksum: stored.draft.artifact_checksum,
  actor_id: "disposable-unverified-reviewer", decision: "approve",
  acknowledged_warning_codes: [...new Set(stored.draft.warnings.map((item: {code:string}) => item.code))].sort(),
});
const prepared = await request(`/api/v1/intake/confirmed-versions/${confirmed.version_id}/research-objects`, {
  record_id: stored.draft.records[0].record_id, name: "Disposable confirmed handoff",
});
const handoffRun = await request("/api/v1/runs", { research_object_id: prepared.research_object_id, prompt: "Confirmed source CBE review", execution_mode: "demo_cbe" });
assert.equal(handoffRun.status, "completed");
const after = await request("/api/v1/runs/metrics");
assert.equal(after.completed, before.completed + 3);
assert.equal(after.failed, before.failed + 3);
console.log("PASS: no-login startup, FASTA intake, real CBE/ABE edits, distinct failures, zero fabricated results, folder placement, checked exports, processor confirmation/handoff and exact completion counts.");
console.log("This uses the real app/pipeline with disposable RAM persistence; it is not a hosted-provider or native-installer acceptance test.");
