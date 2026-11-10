import type { ProvenanceEvent, Run } from "./api/client";

export type StageStatus = NonNullable<ProvenanceEvent["stage_status"]>;

export function stageOutcomeLabel(status: StageStatus, stage: string, runStatus?: Run["status"]): string {
  if (status === "failed") return "Stopped";
  if (status === "pending" && stage === "fields") return "Optional · not recorded";
  if (status === "pending" && runStatus === "failed") return "Not completed";
  if (status === "pending" && runStatus === "completed") return "No completion record";
  return status;
}

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
