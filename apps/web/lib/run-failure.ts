import type { ProvenanceEvent, Run, RunFailure } from "./api/client";
import { STAGES } from "./stages";

export function failureStage(stage?: string | null, code?: string): string {
  if (code?.startsWith("vault_")) return "Vault search";
  if (code === "no_compatible_site") return "Guide selection";
  if (code?.startsWith("intent_") || code === "ai_unavailable") return "Intent interpretation";
  if (code === "schema_invalid") return "Edit validation";
  return STAGES.find(item => item.key === stage)?.label ?? "an unrecorded stage";
}
export function runFailure(run?: Run, events: ProvenanceEvent[] = []): RunFailure | null {
  if (run?.status !== "failed") return null;
  if (run.failure) return run.failure;
  const event = [...events].reverse().find(item => item.stage_status === "failed");
  const recorded = event?.payload?.failure;
  if (recorded && typeof recorded === "object") {
    const issue = recorded as Record<string, unknown>;
    if (["stage", "code", "message", "next_step"].every(key => typeof issue[key] === "string")) return issue as RunFailure;
  }
  return {
    stage: event?.stage ?? run.current_stage ?? "unknown", code: "legacy_reason_unavailable",
    message: "This historical run has no structured explanation recorded.",
    next_step: "Inspect Provenance for any recorded stage details. A missing reason does not mean the vault lacked evidence.",
  };
}
