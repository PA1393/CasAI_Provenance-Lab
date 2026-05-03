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
  fasta_preview: string | null;
  target_region: number[] | null;
};

export type ResearchObjectCreate = {
  name: string;
  input_filename: string;
  input_file_type: string;
  pdb_id: string;
  target_region?: number[];
};

export type Run = {
  run_id: string;
  research_object_id: string;
  created_at: string;
  prompt: string;
  status: "queued" | "running" | "completed" | "failed";
  started_at: string | null;
  completed_at: string | null;
  guide_rna: string | null;
  current_stage: string | null;
};

export type RunCreate = {
  research_object_id: string;
  prompt: string;
};

export type ProvenanceEvent = {
  event_id: string;
  run_id: string;
  stage: string;
  event_type: string;
  message: string;
  payload: Record<string, unknown> | null;
  duration_ms: number | null;
  occurred_at: string;
};

export type Result = {
  result_id: string;
  run_id: string;
  research_object_id: string | null;
  edited_sequence: string | null;
  edit_summary: string | null;
  off_target_score: number | null;
  on_target_score: number | null;
  notes: string | null;
  reproducible: boolean;
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

export async function getRun(runId: string): Promise<Run> {
  return apiFetch<Run>(`/api/v1/runs/${runId}`);
}

export async function createRun(data: RunCreate): Promise<Run> {
  return apiFetch<Run>("/api/v1/runs", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
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
