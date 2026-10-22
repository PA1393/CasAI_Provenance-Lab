import type { ProvenanceEvent, Run } from "@/lib/api/client";
import { STAGES } from "@/lib/stages";
import { stageStatus } from "@/lib/run-progress";

export function RunProgress({ run, provenance }: { run: Run; provenance: ProvenanceEvent[] }) {
  return (
    <section aria-label="Run progress" className="mt-7 rounded-lg border border-border bg-bg-card p-5">
      <ol className="grid gap-3 sm:grid-cols-4 xl:grid-cols-7">
        {STAGES.map((stage, index) => {
          const status = stageStatus(stage.key, provenance.filter((event) => event.stage === stage.key), run.current_stage, run.status);
          return (
            <li key={stage.key} aria-current={status === "running" ? "step" : undefined} className={`flex gap-3 sm:flex-col sm:items-center sm:text-center ${status === "failed" ? "text-accent-red" : status === "running" || status === "completed" ? "text-accent" : "text-muted"}`}>
              <span className={`grid h-8 w-8 shrink-0 place-items-center rounded-full border text-sm font-semibold ${status === "running" || status === "completed" ? "border-accent/30 bg-accent-soft" : "border-border"}`}>{status === "completed" ? "✓" : status === "failed" ? "!" : index + 1}</span>
              <span><span className="block text-xs font-semibold">{stage.label}</span><span className="mt-1 block text-xs capitalize">{status}</span></span>
            </li>
          );
        })}
      </ol>
    </section>
  );
}
