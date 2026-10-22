import { invoke, isTauri } from "@tauri-apps/api/core";

// Public deployment address only. Never put API/service credentials in this bundle.
export const DEFAULT_API_URL = "https://casaiprovenancelab.vercel.app";
export const CONNECTION_STORAGE_KEY = "casai-desktop-api-url";

export function normalizeApiUrl(value: string, allowLoopback = false): string {
  const url = new URL(value.trim());
  if (url.username || url.password || url.search || url.hash) {
    throw new Error("Use a backend URL without credentials, query parameters or fragments.");
  }
  const local = allowLoopback && url.protocol === "http:" &&
    ["localhost", "127.0.0.1", "[::1]"].includes(url.hostname);
  if (!local && (url.protocol !== "https:" || url.origin !== DEFAULT_API_URL)) {
    throw new Error("This demo installer permits only the CasAI Vercel backend. Other hosts require a reviewed configuration change.");
  }
  return url.href.replace(/\/+$/, "");
}

export function loadApiUrl(): string {
  try {
    const saved = localStorage.getItem(CONNECTION_STORAGE_KEY);
    return saved ? normalizeApiUrl(saved, import.meta.env?.DEV ?? false) : DEFAULT_API_URL;
  } catch {
    return DEFAULT_API_URL;
  }
}

let sessionUrl: string | null = null;
let writesEnabled = false;
let checkGeneration = 0;

export function hasRequiredDemoRoutes(value: unknown): boolean {
  if (!value || typeof value !== "object" || !("paths" in value)) return false;
  const paths = value.paths;
  if (!paths || typeof paths !== "object") return false;
  return ["/api/v1/intake/research-drafts", "/api/v1/guide-maps", "/api/v1/simulation-plans"]
    .every((path) => Object.hasOwn(paths, path));
}

export function saveApiUrl(value: string): { url: string; persisted: boolean } {
  const url = normalizeApiUrl(value, import.meta.env?.DEV ?? false);
  sessionUrl = url;
  writesEnabled = false;
  try {
    localStorage.setItem(CONNECTION_STORAGE_KEY, url);
    return { url, persisted: true };
  } catch {
    return { url, persisted: false };
  }
}

export function getPublicEnv() {
  return { NEXT_PUBLIC_API_BASE_URL: sessionUrl ?? loadApiUrl() };
}

export async function fetchApi(url: string, init?: RequestInit): Promise<Response> {
  if ((init?.method ?? "GET") !== "GET" && !writesEnabled) {
    throw new Error("Backend compatibility is not verified. Refresh the connection after deploying the merged API before submitting inputs or runs.");
  }
  if (init?.body != null && typeof init.body !== "string") {
    throw new Error("The desktop API accepts JSON text request bodies only");
  }
  if (typeof window === "undefined" || !isTauri()) return fetch(url, init);
  const target = new URL(url);
  if (target.origin !== DEFAULT_API_URL || target.username || target.password || target.search || target.hash) {
    throw new Error("Desktop transport accepts only the approved CasAI backend");
  }
  if (init?.signal?.aborted) throw new DOMException("Request aborted", "AbortError");
  const result = await invoke<{ status: number; body: string }>("api_request", {
    method: init?.method ?? "GET", path: target.pathname,
    body: typeof init?.body === "string" ? init.body : null,
  });
  if (init?.signal?.aborted) throw new DOMException("Request aborted", "AbortError");
  return new Response(result.body, { status: result.status, headers: { "content-type": "application/json" } });
}

export async function checkConnection(baseUrl: string): Promise<"ready" | "outdated"> {
  const generation = ++checkGeneration;
  writesEnabled = false;
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 8_000);
  try {
    const response = await fetchApi(`${normalizeApiUrl(baseUrl, import.meta.env?.DEV ?? false)}/health`, {
      signal: controller.signal, cache: "no-store", credentials: "omit", redirect: "error",
    });
    if (!response.ok || (await response.json()).status !== "ok") {
      throw new Error("The address did not return a healthy CasAI API.");
    }
    const schema = await fetchApi(`${normalizeApiUrl(baseUrl, import.meta.env?.DEV ?? false)}/openapi.json`, {
      signal: controller.signal, cache: "no-store", credentials: "omit", redirect: "error",
    });
    if (!schema.ok || !hasRequiredDemoRoutes(await schema.json())) return "outdated";
    if (generation === checkGeneration) writesEnabled = true;
    return "ready";
  } finally {
    clearTimeout(timer);
  }
}
