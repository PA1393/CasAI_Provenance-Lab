export type DemoExport = {
  schema_version: "casai.demo-export.v1";
  run_id: string;
  files: { path: string; content: string; encoding: string; byte_length: number; sha256: string }[];
  limitations: string[];
};

// Fixed names only: never turn a backend/user label into a filesystem path.
const expectedFiles = ["input.json", "provenance.json", "results.json", "run.json"];
export async function verifyDemoExport(value: DemoExport, runId: string): Promise<string> {
  if (value.schema_version !== "casai.demo-export.v1" || value.run_id !== runId ||
      !Array.isArray(value.files) || value.files.map(file => file.path).sort().join("|") !== expectedFiles.join("|")) {
    throw new Error("The export does not match this run or package format.");
  }
  for (const file of value.files) {
    if (file.encoding !== "utf-8" || typeof file.content !== "string") throw new Error("Unsupported export encoding.");
    const bytes = new TextEncoder().encode(file.content);
    const digest = await crypto.subtle.digest("SHA-256", bytes);
    const hex = Array.from(new Uint8Array(digest), byte => byte.toString(16).padStart(2, "0")).join("");
    if (bytes.byteLength !== file.byte_length || hex !== file.sha256) throw new Error("Export integrity check failed. Nothing was saved.");
  }
  return JSON.stringify(value, null, 2);
}
