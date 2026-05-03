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
      <section className="px-8 pt-12 pb-12 max-w-4xl mx-auto">
        <Link href="/runs" className="font-mono text-xs tracking-[0.2em] uppercase text-muted hover:text-accent transition-colors">
          ← RUNS
        </Link>
        <div className="mt-6">
          <ErrorState message={`Could not load run: ${id}`} />
        </div>
      </section>
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
    <section className="px-8 pt-12 pb-12 max-w-4xl mx-auto">
      <Link href="/runs" className="font-mono text-xs tracking-[0.2em] uppercase text-muted hover:text-accent transition-colors">
        ← ALL RUNS
      </Link>

      <div className="mt-6 flex items-center gap-3">
        <Eyebrow>──── RUN</Eyebrow>
        <RunStatusBadge status={run.status} />
      </div>

      <h1 className="mt-3 font-serif-display text-3xl md:text-4xl">{run.prompt}</h1>
      <Hash value={run.run_id} length={16} className="mt-2 block" />

      <dl className="mt-8 grid grid-cols-2 gap-4 rounded-lg border border-border bg-bg-card p-6 sm:grid-cols-3">
        <div className="sm:col-span-2">
          <dt className="font-mono text-[10px] tracking-[0.2em] uppercase text-muted font-semibold">
            Research Object
          </dt>
          <dd className="mt-2">
            <Hash value={run.research_object_id} length={20} />
          </dd>
        </div>
        {run.guide_rna && (
          <div className="sm:col-span-1">
            <dt className="font-mono text-[10px] tracking-[0.2em] uppercase text-muted font-semibold">
              Guide RNA
            </dt>
            <dd className="mt-2 font-mono text-xs text-text">{run.guide_rna}</dd>
          </div>
        )}
        <div>
          <dt className="font-mono text-[10px] tracking-[0.2em] uppercase text-muted font-semibold">
            Started
          </dt>
          <dd className="mt-2 text-xs text-text">
            {startedAt ? startedAt.toLocaleString() : "—"}
          </dd>
        </div>
        <div>
          <dt className="font-mono text-[10px] tracking-[0.2em] uppercase text-muted font-semibold">
            Completed
          </dt>
          <dd className="mt-2 text-xs text-text">
            {completedAt ? completedAt.toLocaleString() : "—"}
          </dd>
        </div>
        {durationSec && (
          <div>
            <dt className="font-mono text-[10px] tracking-[0.2em] uppercase text-muted font-semibold">
              Duration
            </dt>
            <dd className="mt-2 text-xs text-accent">{durationSec}s</dd>
          </div>
        )}
      </dl>

      <div className="mt-10">
        <RunTabs provenance={provenance} results={results} currentStage={run.current_stage} />
      </div>
    </section>
  );
}
