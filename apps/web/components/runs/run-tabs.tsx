"use client";

import { useState } from "react";
import type { ProvenanceEvent, Result } from "@/lib/api/client";
import { RunPipeline } from "@/components/runs/run-pipeline";
import { RunSimulation } from "@/components/runs/simulation/run-simulation";
import { extractEditGeometry } from "@/components/runs/simulation/sequence-track";
import { RagSources } from "@/components/runs/rag-sources";

type RagSource = {
  chunk_id: string | null | undefined;
  source_key: string;
  chunk_text: string;
  similarity: number | null | undefined;
  source_path?: string | null;
  source_url?: string | null;
  source_title?: string | null;
  source_type?: string | null;
};

type Props = {
  provenance: ProvenanceEvent[];
  results: Result[];
  currentStage: string | null;
  pdbId?: string | null;
  guideRna?: string | null;
  editedSequence?: string | null;
  sequence?: string | null;
};

type Tab = "simulation" | "provenance" | "results" | "sources";
const tabs: Tab[] = ["results", "simulation", "provenance", "sources"];

function extractRagSources(provenance: ProvenanceEvent[]): RagSource[] {
  const simulateEvent = provenance.find((e) => e.stage === "simulate");
  if (!simulateEvent?.payload) return [];
  const sources = simulateEvent.payload["rag_sources"];
  if (!Array.isArray(sources)) return [];
  return sources as RagSource[];
}

export function RunTabs({
  provenance,
  results,
  currentStage,
  pdbId,
  guideRna,
  editedSequence,
  sequence,
}: Props) {
  const [active, setActive] = useState<Tab>("results");
  const ragSources = extractRagSources(provenance);
  const editGeometry = extractEditGeometry(provenance);

  return (
    <div>
      <div role="tablist" aria-label="Run details" className="flex gap-1 overflow-x-auto rounded-lg border border-border bg-bg-card">
        {tabs.map((tab) => (
          <button
            key={tab}
            id={`tab-${tab}`}
            role="tab"
            aria-selected={active === tab}
            aria-controls={`panel-${tab}`}
            tabIndex={active === tab ? 0 : -1}
            onClick={() => setActive(tab)}
            onKeyDown={(event) => {
              if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) return;
              event.preventDefault();
              const index = tabs.indexOf(tab);
              const next = event.key === "Home" ? tabs[0] : event.key === "End" ? tabs[tabs.length - 1] : tabs[(index + (event.key === "ArrowRight" ? 1 : -1) + tabs.length) % tabs.length];
              setActive(next);
              document.getElementById(`tab-${next}`)?.focus();
            }}
            className={`whitespace-nowrap border-b-2 px-5 py-4 text-sm font-semibold transition-colors ${
              active === tab
                ? "border-accent bg-accent-soft/50 text-accent"
                : "border-transparent text-text-secondary hover:text-text"
            }`}
          >
            {tab === "results" ? "Summary" : tab === "simulation" ? "3D interaction" : tab === "provenance" ? "Provenance" : `Sources${ragSources.length > 0 ? ` (${ragSources.length})` : ""}`}
          </button>
        ))}
      </div>

      <div role="tabpanel" id={`panel-${active}`} aria-labelledby={`tab-${active}`} className="mt-6">
        {active === "simulation" && (
          <RunSimulation
            pdbId={pdbId}
            guideRna={guideRna}
            editedSequence={editedSequence}
            sequence={sequence}
            geometry={editGeometry}
          />
        )}
        {active === "provenance" && (
          <ProvenanceTab events={provenance} currentStage={currentStage} />
        )}
        {active === "results" && <ResultsTab results={results} />}
        {active === "sources" && <RagSources sources={ragSources} />}
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
    <div>
    <p className="mb-5 rounded-lg border border-border bg-accent-soft/40 px-4 py-3 text-sm text-text-secondary">Concept-demo computational results. Scores are heuristics, not measured editing efficiency or experimental validation.</p>
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
                    On-target heuristic score
                  </p>
                  <p className="mt-1 font-serif-display italic text-2xl text-accent">
                    {(result.on_target_score * 100).toFixed(0)} <span className="text-sm text-muted">/ 100</span>
                  </p>
                </div>
              )}
              {result.off_target_score != null && (
                <div>
                  <p className="font-mono text-[10px] tracking-[0.2em] uppercase text-muted font-semibold">
                    Off-target heuristic score
                  </p>
                  <p className="mt-1 font-serif-display italic text-2xl text-text">
                    {(result.off_target_score * 100).toFixed(0)} <span className="text-sm text-muted">/ 100</span>
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
    </div>
  );
}
