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
      <div className="flex gap-1 border-b border-border">
        {(["provenance", "results"] as Tab[]).map((tab) => (
          <button
            key={tab}
            onClick={() => setActive(tab)}
            className={`px-5 py-3 font-mono text-xs tracking-[0.2em] uppercase font-semibold transition-colors ${
              active === tab
                ? "text-accent border-b-2 border-accent -mb-px"
                : "text-muted hover:text-text"
            }`}
          >
            {tab}
          </button>
        ))}
      </div>

      <div className="mt-6">
        {active === "provenance" && (
          <ProvenanceTab events={provenance} currentStage={currentStage} />
        )}
        {active === "results" && <ResultsTab results={results} />}
      </div>
    </div>
  );
}

function ProvenanceTab({
  events,
  currentStage,
}: {
  events: ProvenanceEvent[];
  currentStage: string | null;
}) {
  if (events.length === 0) {
    return <p className="text-sm text-muted">No provenance events recorded yet.</p>;
  }
  return <RunPipeline provenance={events} currentStage={currentStage} />;
}

function ResultsTab({ results }: { results: Result[] }) {
  if (results.length === 0) {
    return (
      <p className="rounded-lg border border-dashed border-border bg-bg-card/50 px-5 py-12 text-center text-sm text-muted">
        No results recorded for this run.
      </p>
    );
  }
  return (
    <ul className="flex flex-col gap-4">
      {results.map((result) => (
        <li
          key={result.result_id}
          className="rounded-lg border border-border bg-bg-card px-5 py-5"
        >
          {result.edit_summary && (
            <p className="text-sm text-text leading-relaxed">{result.edit_summary}</p>
          )}

          {(result.on_target_score != null || result.off_target_score != null) && (
            <div className="mt-4 flex flex-wrap gap-8 border-t border-border pt-4">
              {result.on_target_score != null && (
                <div>
                  <p className="font-mono text-[10px] tracking-[0.2em] uppercase text-muted font-semibold">
                    ON-TARGET EFFICIENCY
                  </p>
                  <p className="mt-1 font-serif-display italic text-2xl text-accent">
                    {(result.on_target_score * 100).toFixed(0)}%
                  </p>
                </div>
              )}
              {result.off_target_score != null && (
                <div>
                  <p className="font-mono text-[10px] tracking-[0.2em] uppercase text-muted font-semibold">
                    OFF-TARGET RISK
                  </p>
                  <p className="mt-1 font-serif-display italic text-2xl text-text">
                    {(result.off_target_score * 100).toFixed(0)}%
                  </p>
                </div>
              )}
              {result.reproducible && (
                <div>
                  <p className="font-mono text-[10px] tracking-[0.2em] uppercase text-muted font-semibold">
                    REPRODUCIBLE
                  </p>
                  <p className="mt-1 font-mono text-sm text-accent-green">✓ YES</p>
                </div>
              )}
            </div>
          )}

          {result.edited_sequence && (
            <div className="mt-4 border-t border-border pt-4">
              <p className="font-mono text-[10px] tracking-[0.2em] uppercase text-muted font-semibold">
                EDITED SEQUENCE
              </p>
              <p className="mt-2 font-mono text-xs text-text break-all">
                {result.edited_sequence}
              </p>
            </div>
          )}

          {result.notes && (
            <p className="mt-4 text-xs text-muted border-t border-border pt-4 italic">
              {result.notes}
            </p>
          )}
        </li>
      ))}
    </ul>
  );
}
