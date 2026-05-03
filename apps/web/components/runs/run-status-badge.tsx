type Props = {
  status: string;
};

const statusStyles: Record<string, string> = {
  queued: "border-accent-amber/60 text-accent-amber",
  pending: "border-accent-amber/60 text-accent-amber",
  running: "border-accent/60 text-accent",
  completed: "border-accent-green/60 text-accent-green",
  complete: "border-accent-green/60 text-accent-green",
  failed: "border-accent-red/60 text-accent-red",
};

export function RunStatusBadge({ status }: Props) {
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
