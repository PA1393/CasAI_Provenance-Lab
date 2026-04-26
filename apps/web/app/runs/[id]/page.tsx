import Link from "next/link";
import { getRun, getRunProvenance, getRunResults } from "@/lib/api/client";
import { RunStatusBadge } from "@/components/runs/run-status-badge";
import { RunTabs } from "@/components/runs/run-tabs";
import { ErrorState } from "@/components/ui/error-state";

type Props = {
  params: Promise<{ id: string }>;
};

export default async function RunPage({ params }: Props) {
  const { id } = await params;

  let run;
  try {
    run = await getRun(id);
  } catch {
    return (
      <div className="mx-auto max-w-3xl">
        <Link href="/runs" className="text-sm text-slate-500 hover:text-accent">
          ← Runs
        </Link>
        <div className="mt-6">
          <ErrorState message={`Could not load run: ${id}`} />
        </div>
      </div>
    );
  }

  const [provenance, results] = await Promise.all([
    getRunProvenance(id).catch(() => []),
    getRunResults(id).catch(() => []),
  ]);

  return (
    <div className="mx-auto max-w-3xl">
      <div className="flex items-start justify-between">
        <div>
          <Link href="/runs" className="text-sm text-slate-500 hover:text-accent">
            ← Runs
          </Link>
          <div className="mt-2 flex items-center gap-3">
            <h1 className="text-2xl font-semibold text-ink">Run</h1>
            <RunStatusBadge status={run.status} />
          </div>
          <p className="mt-1 font-mono text-xs text-slate-400">{run.run_id}</p>
        </div>
      </div>

      <dl className="mt-6 grid grid-cols-2 gap-4 rounded-3xl border border-slate-200/80 bg-white/85 p-5 shadow-sm sm:grid-cols-3">
        <div className="col-span-2 sm:col-span-3">
          <dt className="text-xs text-slate-400">Prompt</dt>
          <dd className="mt-1 text-sm text-slate-700">{run.prompt}</dd>
        </div>
        <div className="sm:col-span-2">
          <dt className="text-xs text-slate-400">Research Object</dt>
          <dd className="mt-1 font-mono text-xs text-slate-500">{run.research_object_id}</dd>
        </div>
        <div>
          <dt className="text-xs text-slate-400">Created</dt>
          <dd className="mt-1 text-xs text-slate-500">{run.created_at}</dd>
        </div>
        {run.started_at && (
          <div>
            <dt className="text-xs text-slate-400">Started</dt>
            <dd className="mt-1 text-xs text-slate-500">{run.started_at}</dd>
          </div>
        )}
        {run.completed_at && (
          <div>
            <dt className="text-xs text-slate-400">Completed</dt>
            <dd className="mt-1 text-xs text-slate-500">{run.completed_at}</dd>
          </div>
        )}
      </dl>

      <div className="mt-8">
        <RunTabs provenance={provenance} results={results} />
      </div>
    </div>
  );
}
