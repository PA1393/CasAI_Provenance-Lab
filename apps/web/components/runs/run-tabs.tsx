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
    return <p className="text-sm text-slate-500">No results available yet.</p>;
  }
  return (
    <ul className="flex flex-col gap-2">
      {results.map((result) => (
        <li
          key={result.result_id}
          className="rounded-2xl border border-slate-200/80 bg-white/85 px-5 py-3 text-sm"
        >
          <div className="flex flex-col gap-1">
            <p className="text-slate-700">{result.edit_summary}</p>
            {result.on_target_score != null && (
              <span className="text-xs text-slate-400">
                On-target: {(result.on_target_score * 100).toFixed(0)}% · Off-target:{" "}
                {((result.off_target_score ?? 0) * 100).toFixed(0)}%
              </span>
            )}
          </div>
        </li>
      ))}
    </ul>
  );
}
