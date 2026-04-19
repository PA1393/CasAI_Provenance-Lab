import { getPublicEnv } from "@casai/env";

// ─── Types ────────────────────────────────────────────────────────────────────

export type ResearchObject = {
  research_object_id: string;
  created_at: string;
  name: string;
  input_filename: string;
  input_file_type: string;
  pdb_id: string;
  mmcif_fetched_from: string | null;
  mmcif_hash: string | null;
  sequence_length: number | null;
  gc_content: number | null;
  avg_phred_score: number | null;
  reads_passing_qc: number | null;
  reads_total: number | null;
  ro_hash: string;
  status: string;
};

export type ResearchObjectCreate = {
  name: string;
  input_filename: string;
  input_file_type: string;
  pdb_id: string;
};

export type Run = {
  run_id: string;
  research_object_id: string;
  status: string;
  mode: string;
};

export type ProvenanceEvent = {
  event_id: string;
  run_id: string;
  event_type: string;
  timestamp: string;
  sequence: number;
};

export type Result = {
  result_id: string;
  run_id: string;
  summary: string;
  status: string;
};

// ─── Base fetch ───────────────────────────────────────────────────────────────

function apiUrl(path: string): string {
  const { NEXT_PUBLIC_API_BASE_URL } = getPublicEnv();
  return `${NEXT_PUBLIC_API_BASE_URL}${path}`;
}

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(apiUrl(path), { cache: "no-store", ...init });
  if (!response.ok) {
    throw new Error(`API error ${response.status}: ${path}`);
  }
  return response.json() as Promise<T>;
}

// ─── Health ───────────────────────────────────────────────────────────────────

export async function getHealth(): Promise<{ status: string }> {
  return apiFetch("/health");
}

// ─── Research Objects ─────────────────────────────────────────────────────────

export async function getResearchObjects(): Promise<ResearchObject[]> {
  const data = await apiFetch<{ items: ResearchObject[] }>("/api/v1/research-objects");
  return data.items;
}

export async function getResearchObject(researchObjectId: string): Promise<ResearchObject> {
  return apiFetch<ResearchObject>(`/api/v1/research-objects/${researchObjectId}`);
}

export async function createResearchObject(data: ResearchObjectCreate): Promise<ResearchObject> {
  return apiFetch<ResearchObject>("/api/v1/research-objects", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
}

// ─── Runs ─────────────────────────────────────────────────────────────────────

export async function getRuns(): Promise<Run[]> {
  const data = await apiFetch<{ items: Run[] }>("/api/v1/runs");
  return data.items;
}

// No single-item endpoint yet on the backend — filter from the list.
export async function getRun(runId: string): Promise<Run> {
  const items = await getRuns();
  const found = items.find((r) => r.run_id === runId);
  if (!found) throw new Error(`Run not found: ${runId}`);
  return found;
}

export async function createRun(
  _data: Omit<Run, "run_id" | "status">,
): Promise<Run> {
  // POST endpoint not yet implemented on the backend.
  throw new Error("createRun: not yet implemented");
}

// ─── Provenance ───────────────────────────────────────────────────────────────

export async function getRunProvenance(runId: string): Promise<ProvenanceEvent[]> {
  const data = await apiFetch<{ items: ProvenanceEvent[] }>(
    `/api/v1/runs/${runId}/provenance`,
  );
  return data.items;
}

// ─── Results ──────────────────────────────────────────────────────────────────

export async function getRunResults(runId: string): Promise<Result[]> {
  const data = await apiFetch<{ items: Result[] }>(`/api/v1/runs/${runId}/results`);
  return data.items;
}
