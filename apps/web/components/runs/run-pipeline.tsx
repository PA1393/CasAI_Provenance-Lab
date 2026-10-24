import type { ProvenanceEvent, Run } from "@/lib/api/client";
import { STAGES } from "../../lib/stages";
import { stageStatus } from "../../lib/run-progress";

type Props = {
  provenance: ProvenanceEvent[];
  currentStage: string | null;
  runStatus?: Run["status"];
};

export function RunPipeline({ provenance, currentStage, runStatus }: Props) {
  const eventsByStage = Object.fromEntries(
    STAGES.map((s) => [s.key, provenance.filter((e) => e.stage === s.key)])
  );

  return (
    <ol className="flex flex-col gap-2">
      {STAGES.map((stage, i) => {
        const events = eventsByStage[stage.key] ?? [];
        const state = stageStatus(stage.key, events, currentStage, runStatus);
        const isActive = stage.key === currentStage && runStatus === "running";
        const isDone = state === "completed";
        const failed = state === "failed";

        return (
          <li
            key={stage.key}
            className={`rounded-lg border px-5 py-4 transition-colors ${
              isActive
                ? "border-accent/60 bg-accent/5"
                : isDone
                  ? "border-border bg-bg-card"
                  : "border-border/50 bg-bg-card/30 opacity-50"
            }`}
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <span
                  className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-full font-mono text-[11px] font-bold ${
                    isDone
                      ? "bg-accent text-bg"
                      : isActive
                        ? "border border-accent text-accent"
                        : "border border-border text-muted"
                  }`}
                >
                  {isDone ? "✓" : i + 1}
                </span>
                <span
                  className={`font-mono text-xs tracking-[0.2em] uppercase font-semibold ${
                    isActive ? "text-accent" : isDone ? "text-text" : "text-muted"
                  }`}
                >
                  {stage.label}
                </span>
              </div>
              {isActive && !failed && !isDone && (
                <span className="animate-pulse-soft font-mono text-[10px] tracking-[0.2em] uppercase text-accent">
                  CURRENT STAGE
                </span>
              )}
            </div>
            <p className="ml-9 mt-2 text-xs capitalize text-text-secondary">{state === "failed" ? "Stopped — review the recorded event below" : state === "pending" ? "No completion evidence recorded" : state}</p>
            {stage.key === "summary" && state === "completed" && <p className="ml-9 mt-2 text-sm text-text-secondary">Run reached its terminal summary state. The Summary tab displays the edit summary stored with the result.</p>}

            {events.map((event) => (
              <div
                key={event.event_id}
                className="mt-3 ml-9 flex items-start justify-between gap-4"
              >
                <span className="text-sm text-muted">{event.message}</span>
                {event.duration_ms != null && (
                  <span className="shrink-0 rounded border border-border bg-bg px-2 py-0.5 font-mono text-[10px] text-muted">
                    {event.duration_ms}ms
                  </span>
                )}
              </div>
            ))}
          </li>
        );
      })}
    </ol>
  );
}
