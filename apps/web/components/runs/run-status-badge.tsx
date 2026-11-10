import { failureStage } from "../../lib/run-failure";
import type { RunFailure } from "../../lib/api/client";
type Props = {
  status: string;
  overview?: boolean;
  stage?: string | null;
  failure?: RunFailure | null;
};

const statusStyles: Record<string, string> = {
  queued: "border-accent-amber/60 text-accent-amber",
  pending: "border-accent-amber/60 text-accent-amber",
  running: "border-accent/60 text-accent",
  completed: "border-accent-green/60 text-accent-green",
  complete: "border-accent-green/60 text-accent-green",
  failed: "border-accent-red/60 text-accent-red",
};

export function RunStatusBadge({ status, stage, failure }: Props) {
  if (status === "failed") return <span className="rounded-full border border-accent-amber/40 px-3 py-1 text-xs text-text-secondary">{stage || failure ? `Stopped at ${failureStage(failure?.stage ?? stage, failure?.code)}` : "Stopped — open run details"}</span>;
  const style = statusStyles[status] ?? "border-border text-muted";
  return (
    <span
      className={`inline-flex items-center gap-2 rounded-full border px-3 py-1 font-mono text-[10px] tracking-[0.2em] uppercase font-semibold ${style}`}
    >
      <span
        className={`h-1.5 w-1.5 rounded-full bg-current ${status === "running" ? "animate-pulse-soft" : ""}`}
      />
      {status}
    </span>
  );
}
