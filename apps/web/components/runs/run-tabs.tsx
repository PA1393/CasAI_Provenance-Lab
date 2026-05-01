"use client";

import { useState } from "react";
import type { ProvenanceEvent, Result } from "@/lib/api/client";
import { RunPipeline } from "@/components/runs/run-pipeline";

type Props = {
  provenance: ProvenanceEvent[];
  results: Result[];
  currentStage: string | null;
};

type Tab = "provenance" | "results";

export function RunTabs({ provenance, results, currentStage }: Props) {
  const [active, setActive] = useState<Tab>("provenance");

  return (
    <div>
      <div className="flex gap-2 border-b border-slate-200">
        {(["provenance", "results"] as Tab[]).map((tab) => (
          <button
            key={tab}
            onClick={() => setActive(tab)}
            className={`rounded-t-xl px-5 py-2.5 text-sm font-medium capitalize transition ${
              active === tab
                ? "-mb-px border border-b-white border-slate-200 bg-white text-ink"
                : "text-slate-500 hover:text-ink"
            }`}
          >
            {tab}
          </button>
        ))}
      </div>

      <div className="mt-5">
        {active === "provenance" && <ProvenanceTab events={provenance} currentStage={currentStage} />}
        {active === "results" && <ResultsTab results={results} />}
      </div>
    </div>
  );
}

function ProvenanceTab({ events, currentStage }: { events: ProvenanceEvent[]; currentStage: string | null }) {
  if (events.length === 0) {
    return <p className="text-sm text-slate-500">No provenance events recorded yet.</p>;
  }
  return <RunPipeline provenance={events} currentStage={currentStage} />;
}

function ResultsTab({ results }: { results: Result[] }) {
  if (results.length === 0) {
    return (
      <p className="rounded-2xl border border-dashed border-slate-200 px-5 py-8 text-center text-sm text-slate-400">
        No results recorded for this run.
      </p>
    );
  }
  return (
    <ul className="flex flex-col gap-4">
      {results.map((result) => (
        <li
          key={result.result_id}
          className="rounded-2xl border border-slate-200/80 bg-white/85 px-5 py-4 text-sm shadow-sm"
        >
          {result.edit_summary && (
            <p className="text-slate-700 leading-relaxed">{result.edit_summary}</p>
          )}

          {(result.on_target_score != null || result.off_target_score != null) && (
            <div className="mt-3 flex gap-6">
              {result.on_target_score != null && (
                <div>
                  <p className="text-xs text-slate-400">On-target efficiency</p>
                  <p className="mt-0.5 text-lg font-semibold text-accent">
                    {(result.on_target_score * 100).toFixed(0)}%
                  </p>
                </div>
              )}
              {result.off_target_score != null && (
                <div>
                  <p className="text-xs text-slate-400">Off-target risk</p>
                  <p className="mt-0.5 text-lg font-semibold text-slate-600">
                    {(result.off_target_score * 100).toFixed(0)}%
                  </p>
                </div>
              )}
              {result.reproducible && (
                <div>
                  <p className="text-xs text-slate-400">Reproducible</p>
                  <p className="mt-0.5 text-sm font-medium text-emerald-600">✓ Yes</p>
                </div>
              )}
            </div>
          )}

          {result.edited_sequence && (
            <div className="mt-3">
              <p className="text-xs text-slate-400">Edited sequence</p>
              <p className="mt-1 font-mono text-xs text-slate-500 break-all">{result.edited_sequence}</p>
            </div>
          )}

          {result.notes && (
            <p className="mt-3 text-xs text-slate-400 border-t border-slate-100 pt-3">{result.notes}</p>
          )}
        </li>
      ))}
    </ul>
  );
}
