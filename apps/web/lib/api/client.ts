import { fetchApi, getPublicEnv } from "@casai/env";
import { ApiError } from "./errors";
import { accessToken, setSession, type Session } from "../auth-session";
import type { DemoExport } from "@/lib/demo-export";
import type { StoredDraft, Confirmation, DatasetInspection, ConfirmedFasta } from "@/lib/intake";
import { parseWorkspaceConnection, type WorkspaceConnection } from "../connection-status";

// ─── Types ────────────────────────────────────────────────────────────────────

export type ResearchObject = {
  folder_id?: string | null;
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
  // Full parsed sequence the pipeline runs against. Null when the research
  // object was created without a FASTA upload.
  sequence: string | null;
  confirmed_version_id?: string | null;
  confirmed_record_id?: string | null;
};

export type ResearchObjectCreate = {
  name: string;
  input_filename: string;
  input_file_type: string;
  pdb_id: string;
  target_region?: number[];
  // Raw FASTA text. Input-only: the backend parses it and stores the sequence
  // plus the fields derived from it. Without it the research object has no
  // sequence and every run against it halts at the input stage.
  fasta_text?: string;
};

export type Run = {
  failure?: RunFailure | null;
  folder_id?: string | null;
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

export type RunFailure = { stage: string; code: string; message: string; next_step: string; details?: string[] };

export type RunCreate = {
  research_object_id: string;
  prompt: string;
  execution_mode?: "assisted" | "demo_cbe" | "demo_abe";
};

export type ProvenanceEvent = {
  event_id: string;
  run_id: string;
  stage: string;
  event_type: string;
  stage_status?: "pending" | "running" | "completed" | "failed" | "unknown";
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
  const writing = (init?.method ?? "GET") !== "GET";
  const signal = init?.signal ?? AbortSignal.timeout(writing ? 120_000 : 15_000);
  let response: Response;
  const headers = new Headers(init?.headers);
  const token = accessToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  try {
    response = await fetchApi(apiUrl(path), {
      cache: "no-store", credentials: "omit", redirect: "error", ...init, headers, signal,
    });
  } catch {
    throw new ApiError(null, writing);
  }
  // A response started by a previous account must never affect the next one.
  if (token && accessToken() !== token) throw new ApiError(401);
  if (response.status === 401 && token) setSession(null);
  if (!response.ok) {
    let code: string | undefined;
    if (response.status === 503) {
      try {
        const data = await response.json() as { detail?: { code?: string } };
        if (["workspace_setup_required", "database_not_configured", "database_unavailable"].includes(data.detail?.code ?? "")) code = data.detail?.code;
      } catch { /* Never expose arbitrary provider bodies. */ }
    }
    throw new ApiError(response.status, writing && response.status >= 500, code);
  }
  try {
    const data = await response.json() as T;
    if (token && accessToken() !== token) throw new ApiError(401);
    return data;
  }
  catch (error) {
    if (error instanceof ApiError) throw error;
    throw new ApiError(null, writing);
  }
}

export async function signIn(email: string, password: string): Promise<void> {
  const session = await apiFetch<Session>("/api/v1/auth/login", { method: "POST",
    headers: { "Content-Type": "application/json" }, body: JSON.stringify({ email, password }) });
  if (!session.access_token || !session.user?.id || !(session.expires_in > 0)) throw new Error("Invalid sign-in response");
  setSession(session);
}
export async function signOut() {
  const token = accessToken();
  setSession(null); // Hide private views immediately, including when the network is down.
  if (!token) return;
  const response = await fetchApi(apiUrl("/api/v1/auth/logout"), {
    method: "POST", headers: { Authorization: `Bearer ${token}` },
    credentials: "omit", redirect: "error", signal: AbortSignal.timeout(15_000),
  });
  if (!response.ok) throw new ApiError(response.status);
}
export type ResearchFolder = { folder_id: string; name: string; created_at: string };
export async function getFolders(): Promise<ResearchFolder[]> {
  return (await apiFetch<{ items: ResearchFolder[] }>("/api/v1/folders")).items;
}
export function createFolder(name: string): Promise<ResearchFolder> {
  return apiFetch("/api/v1/folders", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ name }) });
}
export function placeInFolder(kind: "input" | "run", record_id: string, folder_id: string | null): Promise<{ placed: boolean }> {
  return apiFetch("/api/v1/folders/place", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ kind, record_id, folder_id }) });
}

export async function getDemoCapabilities(): Promise<boolean> {
  const data = await apiFetch<{ schema_version: string; run_execution_modes: string[]; max_sequence_bases: number }>("/api/v1/demo/capabilities");
  return data.schema_version === "casai.demo-capabilities.v1" &&
    Array.isArray(data.run_execution_modes) && ["demo_cbe", "demo_abe"].every(mode => data.run_execution_modes.includes(mode)) &&
    data.max_sequence_bases === 5000;
}

export async function getWorkspaceMode(): Promise<"demo" | "accounts"> {
  const data = await apiFetch<{ access_mode?: string }>("/api/v1/demo/capabilities");
  if (data.access_mode !== "demo" && data.access_mode !== "accounts") throw new Error("Backend workspace mode is unavailable");
  return data.access_mode;
}

export async function getWorkspaceConnection(): Promise<WorkspaceConnection> {
  const data = await apiFetch<unknown>("/api/v1/demo/capabilities");
  return parseWorkspaceConnection(data, getPublicEnv().NEXT_PUBLIC_API_BASE_URL);
}

export function storeIntakeDraft(body: Record<string, unknown>): Promise<StoredDraft> {
  return apiFetch("/api/v1/intake/research-drafts", { method: "POST",
    headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
}
export function resumeIntakeDraft(id: string): Promise<StoredDraft> {
  if (!/^sha256:[0-9a-f]{64}$/.test(id)) throw new Error("Invalid draft identifier");
  return apiFetch(`/api/v1/intake/research-drafts/${id}`);
}
export function confirmIntakeDraft(id: string, body: Record<string, unknown>): Promise<Confirmation> {
  if (!/^sha256:[0-9a-f]{64}$/.test(id)) throw new Error("Invalid draft identifier");
  return apiFetch(`/api/v1/intake/research-drafts/${id}/confirm`, { method: "POST",
    headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
}
export function inspectDatasetText(body: Record<string, unknown>): Promise<DatasetInspection> {
  return apiFetch("/api/v1/intake/datasets/inspect-text", { method: "POST",
    headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
}

export function getConfirmedFasta(id: string): Promise<ConfirmedFasta> {
  if (!/^sha256:[0-9a-f]{64}$/.test(id)) throw new Error("Invalid version identifier");
  return apiFetch(`/api/v1/intake/confirmed-versions/${id}/fasta`);
}
export function prepareConfirmedRunInput(id: string, recordId: string, name: string): Promise<ResearchObject> {
  if (!/^sha256:[0-9a-f]{64}$/.test(id)) throw new Error("Invalid version identifier");
  return apiFetch(`/api/v1/intake/confirmed-versions/${id}/research-objects`, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ record_id: recordId, name }),
  });
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

export type RunMetrics = { completed: number; failed: number; finished: number; pending: number; percent: number | null };
export function getRunMetrics(): Promise<RunMetrics> {
  return apiFetch("/api/v1/runs/metrics");
}

export async function getRun(runId: string): Promise<Run> {
  return apiFetch<Run>(`/api/v1/runs/${runId}`);
}

export async function getRunExport(runId: string): Promise<DemoExport> {
  return apiFetch(`/api/v1/runs/${encodeURIComponent(runId)}/export`);
}

export async function createRun(data: RunCreate): Promise<Run> {
  return apiFetch<Run>("/api/v1/runs", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
}

export async function getRunsByResearchObject(researchObjectId: string): Promise<Run[]> {
  const data = await apiFetch<{ items: Run[] }>(
    `/api/v1/research-objects/${researchObjectId}/runs`,
  );
  return data.items;
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

// ─── RAG ──────────────────────────────────────────────────────────────────────

export type RagChunk = {
  chunk_id: string;
  source_key: string;
  chunk_text: string;
  metadata: Record<string, unknown> | null;
  similarity: number;
  source_path: string | null;
  source_url: string | null;
  source_title: string | null;
  source_type: string | null;
};

export async function searchRag(
  query: string,
  matchCount = 3,
  matchThreshold = 0.0,
): Promise<RagChunk[]> {
  const data = await apiFetch<{ items: RagChunk[] }>("/api/v1/rag/search", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      query,
      match_count: matchCount,
      match_threshold: matchThreshold,
    }),
  });
  return data.items;
}
