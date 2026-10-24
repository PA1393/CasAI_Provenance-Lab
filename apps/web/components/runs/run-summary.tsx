import type { ReactNode } from "react";
import type { ResearchObject, Result, Run } from "@/lib/api/client";
import { heuristicScore, summarizeResults } from "../../lib/result-summary";
import { RunStatusBadge } from "./run-status-badge";

type Props = {
  results: Result[];
  run?: Run;
  researchObject?: ResearchObject | null;
  unavailable?: boolean;
  onProvenance: () => void;
  onInteraction: () => void;
  children?: ReactNode;
};

export function RunSummary({ results, run, researchObject, unavailable, onProvenance, onInteraction, children }: Props) {
  const summary = summarizeResults(results);
  return <div className="grid items-start gap-5 lg:grid-cols-[minmax(0,1fr)_18rem]">
    <div className="min-w-0 space-y-5">
      <section className="rounded-xl border border-border bg-bg-card p-5">
        <h2 className="font-serif-display text-2xl">Run summary</h2>
        <p className="mt-3 text-sm leading-6 text-text-secondary">{unavailable ? "The run's stored results could not be retrieved." : results.length ? results.map(result => result.edit_summary || "A result was stored without an edit summary.").join(" ") : run?.status === "failed" ? "This run stopped before producing a stored result. Open Provenance for the recorded reason." : run?.status === "completed" ? "The run is marked completed, but no result summary is stored. Review Provenance before relying on it." : "A summary will be available after the run records a result."}</p>
        <p className="mt-3 text-xs text-muted">Generated deterministically from recorded results, not an additional AI interpretation.</p>
      </section>
      <div className="grid gap-3 sm:grid-cols-3">
        <SummaryMetric label="On-target heuristic" value={unavailable ? "—" : summary.onTarget} detail="First recorded design; not measured efficiency" />
        <SummaryMetric label="Off-target heuristic" value={unavailable ? "—" : summary.offTarget} detail="First recorded design; not measured risk" />
        <SummaryMetric label="Recorded designs" value={unavailable ? "—" : String(summary.count)} detail="Stored results, not a count passing filters" />
      </div>
      <section className="overflow-hidden rounded-xl border border-border bg-bg-card">
        <h2 className="px-5 py-5 font-serif-display text-2xl">Recorded designs</h2>
        <p className="px-5 pb-4 text-xs text-muted">Shown in backend order. No ranking or recommendation is inferred.</p>
        {unavailable ? <p role="alert" className="px-5 pb-6 text-sm text-accent-amber">Results could not be loaded. Refresh to try again.</p> : results.length === 0 ? <p className="px-5 pb-6 text-sm text-muted">No results recorded for this run.</p> :
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <caption className="sr-only">Recorded designs and heuristic scores</caption>
              <thead className="bg-bg-sunken text-xs text-text-secondary"><tr>
                <th scope="col" className="px-5 py-3">Design</th>
                <th scope="col" className="px-4 py-3">On-target</th>
                <th scope="col" className="px-4 py-3">Off-target</th>
                <th scope="col" className="px-4 py-3">Record</th>
              </tr></thead>
              <tbody>{results.map((result, index) => <tr key={result.result_id} className="border-t border-border">
                <th scope="row" className="max-w-xs px-5 py-4 font-medium"><span className="block">Design {index + 1}</span><span className="mt-1 block break-words text-xs font-normal text-text-secondary">{result.edit_summary ?? "No edit summary recorded"}</span></th>
                <td className="whitespace-nowrap px-4 py-4">{heuristicScore(result.on_target_score)}</td>
                <td className="whitespace-nowrap px-4 py-4">{heuristicScore(result.off_target_score)}</td>
                <td className="px-4 py-4"><span className="rounded-full bg-bg-sunken px-3 py-1 text-xs">Stored</span></td>
              </tr>)}</tbody>
            </table>
          </div>}
        {results.length > 0 && <details className="border-t border-border p-5"><summary className="cursor-pointer text-sm font-semibold text-accent">Sequences and result details</summary><div className="mt-4">{children}</div></details>}
      </section>
      <section className="flex flex-col items-start justify-between gap-4 rounded-xl border border-border bg-bg-card p-5 sm:flex-row sm:items-center">
        <div><h2 className="font-semibold">3D interaction</h2><p className="mt-1 text-sm text-text-secondary">Public structure example · explanatory only. Nothing loads until you choose it.</p></div>
        <button type="button" onClick={onInteraction} className="shrink-0 rounded-lg border border-border-strong px-4 py-3 text-sm font-semibold hover:bg-bg-sunken">Open 3D tab</button>
      </section>
    </div>
    <aside className="space-y-4">
      <section className="rounded-xl border border-border bg-bg-card p-5">
        <h2 className="font-serif-display text-2xl">Run record</h2>
        <dl className="mt-5 divide-y divide-border text-sm">
          <RecordFact label="Input hash" value={researchObject?.ro_hash} mono />
          <RecordFact label="Run ID" value={run?.run_id} mono />
          <RecordFact label="Completed time" value={run?.completed_at ?? undefined} />
          <div className="flex flex-wrap items-center justify-between gap-3 py-4"><dt className="text-text-secondary">Status</dt><dd>{run ? <RunStatusBadge status={run.status} /> : "—"}</dd></div>
        </dl>
        <button type="button" onClick={onProvenance} className="mt-4 w-full rounded-lg bg-accent px-4 py-3 text-sm font-semibold text-bg hover:bg-accent-bright">View provenance</button>
      </section>
      <p className="rounded-xl border border-border bg-accent-soft/40 p-4 text-xs leading-6 text-text-secondary">Research preview — based on supplied sequences, computational edit rules and available public structure references. Scores and 3D scenes are exploratory, not experimentally validated predictions.</p>
    </aside>
  </div>;
}

function SummaryMetric({ label, value, detail }: { label: string; value: string; detail: string }) {
  return <section className="rounded-xl border border-border bg-bg-card p-5"><h2 className="text-sm font-semibold">{label}</h2><p className="mt-4 font-serif-display text-3xl">{value}</p><p className="mt-2 text-xs leading-5 text-muted">{detail}</p></section>;
}

function RecordFact({ label, value, mono }: { label: string; value?: string; mono?: boolean }) {
  return <div className="py-4"><dt className="text-text-secondary">{label}</dt><dd className={`mt-2 break-all text-xs ${mono ? "font-mono" : ""}`}>{value || "—"}</dd></div>;
}
