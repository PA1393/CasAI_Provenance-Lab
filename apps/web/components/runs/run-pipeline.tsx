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
    <ol className="flex flex-col gap-3">
      {STAGES.map((stage) => {
        const events = eventsByStage[stage.key] ?? [];
        const isActive = stage.key === currentStage;
        const isDone = events.length > 0;

        return (
          <li
            key={stage.key}
            className={`rounded-2xl border px-5 py-3 text-sm transition ${
              isActive
                ? "border-accent bg-accent/5"
                : isDone
                  ? "border-slate-200/80 bg-white/85"
                  : "border-slate-100 bg-slate-50/50 opacity-50"
            }`}
          >
            <div className="flex items-center justify-between">
              <span className={`font-medium ${isActive ? "text-accent" : "text-slate-700"}`}>
                {stage.label}
              </span>
              {isActive && (
                <span className="text-xs text-accent">running</span>
              )}
            </div>

            {events.map((event) => (
              <div key={event.event_id} className="mt-2 flex items-start justify-between gap-4">
                <span className="text-slate-500">{event.message}</span>
                {event.duration_ms != null && (
                  <span className="shrink-0 text-xs text-slate-400">
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
