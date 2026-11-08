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
  sources: RagSource[];
  run?: Run;
  provenance?: ProvenanceEvent[];
};

export function RagSources({ sources, run, provenance = [] }: Props) {
  const issue = runFailure(run, provenance);
  const mode = provenance.find(event => event.event_type === "input_validated")?.payload?.execution_mode;
  if (sources.length === 0) {
    return (
      <p className="rounded-lg border border-dashed border-border bg-bg-card/50 px-5 py-12 text-center text-sm text-muted">
        {mode === "demo_cbe" || mode === "demo_abe" ? "This rule-based demonstration does not use the vault. Its completed status does not establish evidence for the biological objective."
          : issue?.code.startsWith("vault_") ? `${issue.message} ${issue.next_step}`
          : "No reference sources were recorded for this run. Vault coverage cannot be inferred from an empty source list."}
      </p>
    );
  }

  return (
    <ul className="flex flex-col gap-3">
      {sources.map((source, i) => (
        <li
          key={source.chunk_id ?? i}
          className="rounded-lg border border-border bg-bg-card px-5 py-4"
        >
          <div className="flex items-center justify-between gap-4">
            <div className="flex flex-col gap-0.5 min-w-0">
              <p className="font-mono text-[10px] tracking-[0.2em] uppercase text-accent font-semibold truncate">
                {source.source_title ?? source.source_path ?? source.source_key}
              </p>
              {source.source_type && (
                <p className="font-mono text-[9px] tracking-[0.15em] uppercase text-muted">
                  {source.source_type}
                </p>
              )}
            </div>
            <div className="flex items-center gap-3 shrink-0">
              {source.source_url && (
                <a
                  href={source.source_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="font-mono text-[10px] tracking-[0.15em] uppercase text-accent hover:underline"
                >
                  source ↗
                </a>
              )}
              {source.similarity != null && (
                <span className="font-mono text-[10px] tracking-[0.15em] uppercase text-muted">
                  Similarity {source.similarity.toFixed(2)} · not accuracy
                </span>
              )}
            </div>
          </div>
          <p className="mt-2 text-sm text-text leading-relaxed line-clamp-4">
            {source.chunk_text}
          </p>
        </li>
      ))}
    </ul>
  );
}
import type { Run, ProvenanceEvent } from "../../lib/api/client";
import { runFailure } from "../../lib/run-failure";
