import Link from "next/link";
import type { Run } from "@/lib/api/client";
import { RunStatusBadge } from "./run-status-badge";

type Props = {
  run: Run;
};

export function RunCard({ run }: Props) {
  const { run_id, research_object_id, status, mode } = run;
  return (
    <Link
      href={`/runs/${run_id}`}
      className="group block rounded-3xl border border-slate-200/80 bg-white/85 p-5 shadow-sm transition hover:border-accent/40 hover:shadow-md"
    >
      <div className="flex items-start justify-between gap-3">
        <p className="truncate font-mono text-xs text-slate-400">{run_id}</p>
        <RunStatusBadge status={status} />
      </div>
      <dl className="mt-3 grid grid-cols-2 gap-2 text-sm">
        <div>
          <dt className="text-xs text-slate-400">Mode</dt>
          <dd className="font-medium text-slate-700">{mode}</dd>
        </div>
        <div>
          <dt className="text-xs text-slate-400">Research Object</dt>
          <dd className="truncate font-mono text-xs text-slate-500">{research_object_id}</dd>
        </div>
      </dl>
    </Link>
  );
}
