import type { ProvenanceEvent, Run } from "./api/client";

export type StageStatus = NonNullable<ProvenanceEvent["stage_status"]>;

export function stageStatus(stage: string, events: ProvenanceEvent[], currentStage: string | null, runStatus?: Run["status"]): StageStatus {
  if (stage === currentStage && runStatus === "failed") return "failed";
  if (events.some((event) => event.stage_status === "failed")) return "failed";
  if (stage === currentStage && runStatus === "running") return "running";
  if (stage === "summary" && runStatus === "completed") return "completed";
  if (events.some((event) => event.stage_status === "completed")) return "completed";
  if (events.some((event) => event.stage_status === "running")) return "running";
  if (events.some((event) => !event.stage_status || event.stage_status === "unknown")) return "unknown";
  return "pending";
}
