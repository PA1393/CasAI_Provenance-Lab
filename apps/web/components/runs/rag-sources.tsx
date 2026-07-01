type RagSource = {
  chunk_id: string | null | undefined;
  source_key: string;
  chunk_text: string;
  similarity: number | null | undefined;
};

type Props = {
  sources: RagSource[];
};

export function RagSources({ sources }: Props) {
  if (sources.length === 0) {
    return (
      <p className="rounded-lg border border-dashed border-border bg-bg-card/50 px-5 py-12 text-center text-sm text-muted">
        No vault sources retrieved for this run.
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
            <p className="font-mono text-[10px] tracking-[0.2em] uppercase text-accent font-semibold">
              {source.source_key}
            </p>
            {source.similarity != null && (
              <span className="font-mono text-[10px] tracking-[0.15em] uppercase text-muted">
                {(source.similarity * 100).toFixed(0)}% match
              </span>
            )}
          </div>
          <p className="mt-2 text-sm text-text leading-relaxed line-clamp-4">
            {source.chunk_text}
          </p>
        </li>
      ))}
    </ul>
  );
}
