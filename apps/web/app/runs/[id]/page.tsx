import Link from "next/link";
import {
  getResearchObject,
  getRun,
  getRunProvenance,
  getRunResults,
} from "@/lib/api/client";
import { RunStatusBadge } from "@/components/runs/run-status-badge";
import { RunTabs } from "@/components/runs/run-tabs";
import { RunProgress } from "@/components/runs/run-progress";
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

  const [provenanceResponse, resultsResponse, objectResponse] = await Promise.allSettled([
    getRunProvenance(id),
    getRunResults(id),
    getResearchObject(run.research_object_id),
  ]);
  const provenance = provenanceResponse.status === "fulfilled" ? provenanceResponse.value : [];
  const results = resultsResponse.status === "fulfilled" ? resultsResponse.value : [];
  const researchObject = objectResponse.status === "fulfilled" ? objectResponse.value : null;

  const editedSequence = results.find((r) => r.edited_sequence)?.edited_sequence ?? null;

  const completedAt = run.completed_at ? new Date(run.completed_at) : null;
  const startedAt = run.started_at ? new Date(run.started_at) : null;
  const durationSec =
    completedAt && startedAt
      ? ((completedAt.getTime() - startedAt.getTime()) / 1000).toFixed(1)
      : null;

  return (
    <section className="mx-auto max-w-[92rem] px-4 pb-14 pt-7 sm:px-6 lg:px-8 lg:pt-9">
      <Link href="/runs" className="font-mono text-xs tracking-[0.2em] uppercase text-muted hover:text-accent transition-colors">
        ← ALL RUNS
      </Link>

      <div className="mt-6 flex items-center gap-3">
        <Eyebrow>{run.status === "completed" ? "Results" : "Run progress"}</Eyebrow>
        <RunStatusBadge status={run.status} />
      </div>

      <h1 className="mt-3 font-serif-display text-3xl md:text-4xl">{run.status === "completed" ? "Results" : "Run progress"}</h1>
      <p className="mt-3 text-sm leading-6 text-text-secondary">{run.prompt}</p>
      <Hash value={run.run_id} length={16} className="mt-2 block" />

      <details className="mt-5 rounded-xl border border-border bg-bg-card p-5" open={run.status !== "completed"}>
        <summary className="cursor-pointer text-sm font-semibold">Processing stages</summary>
        {provenanceResponse.status === "rejected" ? <p role="alert" className="mt-4 text-sm text-accent-amber">Stage history could not be loaded.</p> : <RunProgress run={run} provenance={provenance} />}
      </details>

      <details className="mt-4 rounded-xl border border-border bg-bg-card p-5">
      <summary className="cursor-pointer text-sm font-semibold">Input and timing details</summary>
      <dl className="mt-5 grid grid-cols-2 gap-4 sm:grid-cols-3">
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
      </details>

      <div className="mt-10">
        <RunTabs
          provenance={provenance}
          results={results}
          currentStage={run.current_stage}
          pdbId={researchObject?.pdb_id}
          guideRna={run.guide_rna}
          editedSequence={editedSequence}
          sequence={researchObject?.sequence}
          run={run}
          researchObject={researchObject}
          resultsUnavailable={resultsResponse.status === "rejected"}
          provenanceUnavailable={provenanceResponse.status === "rejected"}
        />
      </div>
    </section>
  );
}
