import type { ProvenanceEvent, Run } from "./api/client";

export type StageStatus = "pending" | "running" | "completed" | "failed";

export function stageStatus(stage: string, events: ProvenanceEvent[], currentStage: string | null, runStatus?: Run["status"]): StageStatus {
  if (stage === currentStage && runStatus === "failed") return "failed";
  if (events.some((event) => /(?:failed|invalid|error|rejected)$/.test(event.event_type))) return "failed";
  if (stage === currentStage && runStatus === "running") return "running";
  if (stage === "summary" && runStatus === "completed") return "completed";
  if (events.some((event) => /(?:validated|resolved|executed|scored|packaged|completed)$/.test(event.event_type))) return "completed";
  return "pending";
}
