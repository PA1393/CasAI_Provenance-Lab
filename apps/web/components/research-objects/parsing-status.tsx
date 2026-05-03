// Placeholder — parsing state will be driven by backend events once the pipeline is wired up.
type Props = {
  status?: "ready" | "parsing" | "error";
};

const styles: Record<string, string> = {
  ready: "border-accent/60 text-accent",
  parsing: "border-accent-amber/60 text-accent-amber",
  error: "border-accent-red/60 text-accent-red",
};

const labels: Record<string, string> = {
  ready: "READY",
  parsing: "PARSING…",
  error: "PARSE ERROR",
};

export function ParsingStatus({ status = "ready" }: Props) {
  return (
    <span
      className={`inline-flex items-center gap-2 rounded-full border px-3 py-1 font-mono text-[10px] tracking-[0.2em] font-semibold ${styles[status]}`}
    >
      <span className={`h-1.5 w-1.5 rounded-full bg-current ${status === "parsing" ? "animate-pulse-soft" : ""}`} />
      {labels[status]}
    </span>
  );
}
