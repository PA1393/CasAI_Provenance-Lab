import type { ProvenanceEvent } from "./api/client";
export type RunSource = {
  chunk_id: string | null; source_key: string; chunk_text: string;
  similarity: number | null; source_path?: string | null; source_url?: string | null;
  source_title?: string | null; source_type?: string | null;
};
export function recordedRunSources(events: ProvenanceEvent[]): RunSource[] {
  const event = events.find(item => item.event_type === "intent_resolved" && Array.isArray(item.payload?.rag_sources))
    ?? events.find(item => item.stage === "simulate" && Array.isArray(item.payload?.rag_sources));
  const items = event?.payload?.rag_sources;
  if (!Array.isArray(items)) return [];
  return items.filter(item => item && typeof item === "object" &&
    typeof item.source_key === "string" && typeof item.chunk_text === "string").map(item => ({
      chunk_id: typeof item.chunk_id === "string" ? item.chunk_id : null,
      source_key: item.source_key, chunk_text: item.chunk_text,
      similarity: typeof item.similarity === "number" && Number.isFinite(item.similarity) &&
        item.similarity >= 0 && item.similarity <= 1 ? item.similarity : null,
      ...Object.fromEntries(["source_path", "source_title", "source_type"].map(key => [key, typeof item[key] === "string" ? item[key] : null])),
      source_url: typeof item.source_url === "string" && /^https?:\/\//i.test(item.source_url) ? item.source_url : null,
    }));
}
