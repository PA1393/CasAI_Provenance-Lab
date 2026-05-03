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
            className={`rounded-2xl border px-5 py-3 text-sm transition ${
              isActive
                ? "border-accent/60 bg-accent/5"
                : isDone
                  ? "border-slate-200/80 bg-white/85"
                  : "border-slate-100 bg-slate-50/40 opacity-40"
            }`}
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <span
                  className={`flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-[10px] font-bold ${
                    isDone
                      ? "bg-accent text-white"
                      : isActive
                        ? "border border-accent text-accent"
                        : "border border-slate-200 text-slate-300"
                  }`}
                >
                  {isDone ? "✓" : i + 1}
                </span>
                <span className={`font-medium ${isActive ? "text-accent" : isDone ? "text-slate-700" : "text-slate-400"}`}>
                  {stage.label}
                </span>
              </div>
              {isActive && (
                <span className="animate-pulse-soft text-xs text-accent">running</span>
              )}
            </div>

            {events.map((event) => (
              <div key={event.event_id} className="mt-2 ml-8 flex items-start justify-between gap-4">
                <span className="text-slate-500">{event.message}</span>
                {event.duration_ms != null && (
                  <span className="shrink-0 rounded-full bg-slate-100 px-2 py-0.5 text-[10px] text-slate-400">
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
