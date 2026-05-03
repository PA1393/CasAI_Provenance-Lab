import type { ProvenanceEvent } from "@/lib/api/client";
import { STAGES } from "@/lib/stages";

type Props = {
  provenance: ProvenanceEvent[];
  currentStage: string | null;
};

export function RunPipeline({ provenance, currentStage }: Props) {
  const eventsByStage = Object.fromEntries(
    STAGES.map((s) => [s.key, provenance.filter((e) => e.stage === s.key)])
  );

  return (
    <ol className="flex flex-col gap-2">
      {STAGES.map((stage, i) => {
        const events = eventsByStage[stage.key] ?? [];
        const isActive = stage.key === currentStage;
        const isDone = events.length > 0;

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
              {isActive && (
                <span className="animate-pulse-soft font-mono text-[10px] tracking-[0.2em] uppercase text-accent">
                  RUNNING
                </span>
              )}
            </div>

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
