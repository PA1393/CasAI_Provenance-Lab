// Placeholder — parsing state will be driven by backend events once the pipeline is wired up.
type Props = {
  status?: "ready" | "parsing" | "error";
};

const styles: Record<string, string> = {
  ready: "bg-accentSoft text-accent",
  parsing: "bg-yellow-50 text-yellow-700",
  error: "bg-red-50 text-red-700",
};

const labels: Record<string, string> = {
  ready: "Ready",
  parsing: "Parsing…",
  error: "Parse error",
};

export function ParsingStatus({ status = "ready" }: Props) {
  return (
    <span className={`inline-block rounded-full px-3 py-1 text-xs font-semibold ${styles[status]}`}>
      {labels[status]}
    </span>
  );
}
