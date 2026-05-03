import Link from "next/link";
import type { Run } from "@/lib/api/client";
import { RunStatusBadge } from "./run-status-badge";

type Props = {
  run: Run;
};

export function RunCard({ run }: Props) {
  const { run_id, research_object_id, status, prompt } = run;
  return (
    <Link
      href={`/runs/${run_id}`}
      className="group block rounded-lg border border-border bg-bg-card p-5 hover:border-accent/60 transition-colors"
    >
      <div className="flex items-start justify-between gap-3">
        <p className="truncate font-mono text-xs text-muted">{run_id}</p>
        <RunStatusBadge status={status} />
      </div>
      <dl className="mt-4 grid grid-cols-2 gap-2">
        <div className="col-span-2">
          <dt className="font-mono text-[10px] tracking-[0.2em] uppercase text-muted font-semibold">
            PROMPT
          </dt>
          <dd className="mt-1 truncate text-sm text-text group-hover:text-accent transition-colors">
            {prompt}
          </dd>
        </div>
        <div className="col-span-2">
          <dt className="font-mono text-[10px] tracking-[0.2em] uppercase text-muted font-semibold">
            RESEARCH OBJECT
          </dt>
          <dd className="mt-1 truncate font-mono text-xs text-muted">{research_object_id}</dd>
        </div>
      </dl>
    </Link>
  );
}
