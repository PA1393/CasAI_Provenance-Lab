import type { Result } from "./api/client";

// API scores are normalized heuristics. Reject invalid values rather than
// inventing a zero, clamping, or displaying them as measured percentages.
export function heuristicScore(value: number | null | undefined): string {
  return typeof value === "number" && Number.isFinite(value) && value >= 0 && value <= 1
    ? `${(value * 100).toFixed(0)} / 100`
    : "—";
}

export function summarizeResults(results: Result[]) {
  const first = results[0];
  return {
    onTarget: heuristicScore(first?.on_target_score),
    offTarget: heuristicScore(first?.off_target_score),
    count: results.length,
  };
}
