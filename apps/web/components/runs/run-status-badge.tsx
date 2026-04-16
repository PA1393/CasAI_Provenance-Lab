type Props = {
  status: string;
};

const statusStyles: Record<string, string> = {
  pending: "bg-yellow-50 text-yellow-700",
  running: "bg-blue-50 text-blue-700",
  complete: "bg-accentSoft text-accent",
  failed: "bg-red-50 text-red-700",
};

export function RunStatusBadge({ status }: Props) {
  const style = statusStyles[status] ?? "bg-slate-100 text-slate-600";
  return (
    <span className={`inline-block rounded-full px-3 py-1 text-xs font-semibold ${style}`}>
      {status}
    </span>
  );
}
