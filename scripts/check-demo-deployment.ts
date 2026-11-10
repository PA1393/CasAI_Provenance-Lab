/** Non-mutating public API preflight. No credentials, research reads or writes. */
import { parseWorkspaceConnection, connectionCopy } from "../apps/web/lib/connection-status";

async function main() {
  const argument = process.argv[2];
  if (!argument) throw new Error("Usage: bun scripts/check-demo-deployment.ts https://your-api-host");
  const base = new URL(argument);
  if (base.username || base.password || base.search || base.hash || base.pathname !== "/" ||
    (base.protocol !== "https:" && !(base.protocol === "http:" && ["localhost", "127.0.0.1", "[::1]"].includes(base.hostname)))) {
    throw new Error("Use an HTTPS API origin without credentials, path, query or fragment (loopback HTTP is allowed).");
  }
  async function read(path: string) {
    const response = await fetch(new URL(path, base), { method: "GET", redirect: "error", credentials: "omit", signal: AbortSignal.timeout(15_000) });
    if (!response.ok) throw new Error(`${path}: HTTP ${response.status}; deploy the matching API before proceeding.`);
    return response.json();
  }
  const health = await read("/health") as { status?: unknown };
  if (health.status !== "ok") throw new Error("Health response is incompatible.");
  console.log("PASS: API health endpoint.");
  const capabilities = await read("/api/v1/demo/capabilities");
  const connection = parseWorkspaceConnection(capabilities, base.origin);
  if (capabilities.max_sequence_bases !== 5000 || !Array.isArray(capabilities.run_execution_modes) ||
    !["demo_cbe", "demo_abe"].every(mode => capabilities.run_execution_modes.includes(mode))) {
    throw new Error("Demo execution contract is incompatible.");
  }
  console.log(`PASS: Matching demo contract. ${connectionCopy(connection).label}.`);
  console.log("NOT VERIFIED: database migrations, restart persistence, access isolation or native installers. Complete the release checklist on an authorized staging workspace. No research records were read or written.");
}
main().catch(error => { console.error(error instanceof Error ? error.message : "Deployment check failed."); process.exitCode = 1; });
