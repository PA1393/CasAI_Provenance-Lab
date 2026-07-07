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
  answer?: string | null;
};

export function RagSources({ sources, answer }: Props) {
  if (sources.length === 0 && !answer) {
    return (
      <p className="rounded-lg border border-dashed border-border bg-bg-card/50 px-5 py-12 text-center text-sm text-muted">
        No vault sources retrieved for this run.
      </p>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      {answer && (
        <div className="rounded-lg border border-accent/40 bg-accent/5 px-5 py-4">
          <p className="font-mono text-[10px] tracking-[0.2em] uppercase text-accent font-semibold">
            Generated Answer
          </p>
          <p className="mt-2 text-sm text-text leading-relaxed whitespace-pre-wrap">
            {answer}
          </p>
        </div>
      )}

      {sources.length > 0 && (
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
                      {(source.similarity * 100).toFixed(0)}% match
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
      )}
    </div>
  );
}
