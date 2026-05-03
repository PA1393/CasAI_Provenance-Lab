import Link from "next/link";
import { getRun, getRunProvenance, getRunResults } from "@/lib/api/client";
import { RunStatusBadge } from "@/components/runs/run-status-badge";
import { RunTabs } from "@/components/runs/run-tabs";
import { ErrorState } from "@/components/ui/error-state";
import { Hash } from "@/components/ui/hash";
import { Eyebrow } from "@/components/ui/eyebrow";

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

  const completedAt = run.completed_at ? new Date(run.completed_at) : null;
  const startedAt = run.started_at ? new Date(run.started_at) : null;
  const durationSec =
    completedAt && startedAt
      ? ((completedAt.getTime() - startedAt.getTime()) / 1000).toFixed(1)
      : null;

  return (
    <div className="mx-auto max-w-3xl">
      <Link href="/runs" className="text-sm text-slate-500 hover:text-accent">
        ← All runs
      </Link>

      <div className="mt-4 flex items-center gap-3">
        <Eyebrow>Run</Eyebrow>
        <RunStatusBadge status={run.status} />
      </div>

      <div className="mt-1 flex items-center gap-2">
        <h1 className="text-2xl font-semibold text-ink">{run.prompt}</h1>
      </div>
      <Hash value={run.run_id} length={16} className="mt-1" />

      <dl className="mt-6 grid grid-cols-2 gap-4 rounded-3xl border border-slate-200/80 bg-white/85 p-5 shadow-sm sm:grid-cols-3">
        <div className="sm:col-span-2">
          <dt className="text-xs text-slate-400">Research Object</dt>
          <dd className="mt-1">
            <Hash value={run.research_object_id} length={20} />
          </dd>
        </div>
        {run.guide_rna && (
          <div className="sm:col-span-1">
            <dt className="text-xs text-slate-400">Guide RNA</dt>
            <dd className="mt-1 font-mono text-xs text-slate-600">{run.guide_rna}</dd>
          </div>
        )}
        <div>
          <dt className="text-xs text-slate-400">Started</dt>
          <dd className="mt-1 text-xs text-slate-500">
            {startedAt ? startedAt.toLocaleString() : "—"}
          </dd>
        </div>
        <div>
          <dt className="text-xs text-slate-400">Completed</dt>
          <dd className="mt-1 text-xs text-slate-500">
            {completedAt ? completedAt.toLocaleString() : "—"}
          </dd>
        </div>
        {durationSec && (
          <div>
            <dt className="text-xs text-slate-400">Duration</dt>
            <dd className="mt-1 text-xs text-slate-500">{durationSec}s</dd>
          </div>
        )}
      </dl>

      <div className="mt-8">
        <RunTabs provenance={provenance} results={results} currentStage={run.current_stage} />
      </div>
    </div>
  );
}
