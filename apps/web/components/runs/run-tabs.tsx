"use client";

import { useState } from "react";
import type { ProvenanceEvent, Result } from "@/lib/api/client";

type Props = {
  provenance: ProvenanceEvent[];
  results: Result[];
};

type Tab = "provenance" | "results";

export function RunTabs({ provenance, results }: Props) {
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
        {active === "provenance" && <ProvenanceTab events={provenance} />}
        {active === "results" && <ResultsTab results={results} />}
      </div>
    </div>
  );
}

function ProvenanceTab({ events }: { events: ProvenanceEvent[] }) {
  if (events.length === 0) {
    return <p className="text-sm text-slate-500">No provenance events recorded yet.</p>;
  }
  return (
    <ol className="flex flex-col gap-2">
      {events.map((event) => (
        <li
          key={event.event_id}
          className="rounded-2xl border border-slate-200/80 bg-white/85 px-5 py-3 text-sm"
        >
          <span className="font-medium text-slate-700">{event.event_type}</span>
          <span className="ml-3 text-slate-400">{event.occurred_at}</span>
        </li>
      ))}
    </ol>
  );
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
            {result.confidence != null && (
              <span className="text-xs text-slate-400">
                Confidence: {(result.confidence * 100).toFixed(0)}% · Off-target:{" "}
                {((result.off_target_score ?? 0) * 100).toFixed(0)}%
              </span>
            )}
          </div>
        </li>
      ))}
    </ul>
  );
}
