import { afterEach, expect, test } from "bun:test";
import { checkConnection, DEFAULT_API_URL, fetchApi, hasRequiredDemoRoutes, normalizeApiUrl } from "../src/connection";

const compatible = { paths: {
  "/api/v1/intake/research-drafts": { post: {} },
  "/api/v1/intake/research-drafts/{draft_id}": { get: {} },
  "/api/v1/intake/research-drafts/{draft_id}/confirm": { post: {} },
  "/api/v1/intake/datasets/inspect-text": { post: {} },
  "/api/v1/intake/confirmed-versions/{version_id}/fasta": { get: {} },
  "/api/v1/intake/confirmed-versions/{version_id}/research-objects": { post: {} },
  "/api/v1/runs/{run_id}/export": { get: {} },
  "/api/v1/guide-maps": { post: {} }, "/api/v1/simulation-plans": { post: {} },
} };

const originalFetch = globalThis.fetch;
afterEach(() => { globalThis.fetch = originalFetch; });

test("only the reviewed HTTPS backend is accepted in packaged builds", () => {
  expect(normalizeApiUrl(` ${DEFAULT_API_URL}/ `)).toBe(DEFAULT_API_URL);
  for (const value of ["https://example.org", "http://localhost:8000", "http://127.0.0.1:8000", "file:///tmp/api", "javascript:alert(1)", `${DEFAULT_API_URL}?token=secret`, "https://user:secret@casaiprovenancelab.vercel.app", `${DEFAULT_API_URL}#token`, "https://casaiprovenancelab.vercel.app.evil.example"]) {
    expect(() => normalizeApiUrl(value)).toThrow();
  }
});

test("HTTP is restricted to exact loopback hosts and requires development opt-in", () => {
  expect(normalizeApiUrl("http://127.0.0.1:8000", true)).toBe("http://127.0.0.1:8000");
  expect(() => normalizeApiUrl("http://localhost.evil.example", true)).toThrow();
  expect(() => normalizeApiUrl("http://192.168.1.2:8000", true)).toThrow();
});

test("connection check requires the API health contract and never sends credentials", async () => {
  let options: RequestInit | undefined;
  globalThis.fetch = (async (url, init) => {
    expect([`${DEFAULT_API_URL}/health`, `${DEFAULT_API_URL}/openapi.json`]).toContain(String(url));
    options = init;
    return Response.json(String(url).endsWith("/health") ? { status: "ok" } : compatible);
  }) as typeof fetch;
  expect(await checkConnection(DEFAULT_API_URL)).toBe("ready");
  expect(options?.credentials).toBe("omit");
  expect(options?.redirect).toBe("error");
  globalThis.fetch = (async () => Response.json({ status: "different-service" })) as typeof fetch;
  await expect(checkConnection(DEFAULT_API_URL)).rejects.toThrow();
});

test("reachable old backends are not treated as compatible and cannot receive submissions", async () => {
  globalThis.fetch = (async (url) => Response.json(String(url).endsWith("/health") ? { status: "ok" } : { paths: {} })) as typeof fetch;
  expect(await checkConnection(DEFAULT_API_URL)).toBe("outdated");
  await expect(fetchApi(`${DEFAULT_API_URL}/api/v1/runs`, { method: "POST", body: "{}" })).rejects.toThrow("compatibility");
});

test("compatibility checks reject absent, malformed and incomplete route inventories", () => {
  for (const value of [null, {}, { paths: [] }, { paths: { "/api/v1/guide-maps": {} } }]) {
    expect(hasRequiredDemoRoutes(value)).toBe(false);
  }
  expect(hasRequiredDemoRoutes(compatible)).toBe(true);
});

test("each new desktop action requires its HTTP operation before submissions are enabled", async () => {
  for (const [path, operation] of Object.entries(compatible.paths)) {
    for (const replacement of [undefined, {}, { parameters: [] }, { [Object.keys(operation)[0]]: null }]) {
      const incomplete = { paths: { ...compatible.paths, [path]: replacement } };
      globalThis.fetch = (async (url) => Response.json(String(url).endsWith("/health") ? { status: "ok" } : incomplete)) as typeof fetch;
      expect(await checkConnection(DEFAULT_API_URL)).toBe("outdated");
      await expect(fetchApi(`${DEFAULT_API_URL}/api/v1/runs`, { method: "POST", body: "{}" })).rejects.toThrow("compatibility");
    }
  }
});

test("HTML, unavailable endpoints and network errors are not reported connected", async () => {
  for (const response of [new Response("<html>login</html>"), new Response("offline", { status: 503 })]) {
    globalThis.fetch = (async () => response) as typeof fetch;
    await expect(checkConnection(DEFAULT_API_URL)).rejects.toThrow();
  }
  globalThis.fetch = (async () => { throw new TypeError("network unavailable"); }) as typeof fetch;
  await expect(checkConnection(DEFAULT_API_URL)).rejects.toThrow();
});
