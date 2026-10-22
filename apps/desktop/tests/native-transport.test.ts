import { afterEach, expect, test } from "bun:test";
import { clearMocks, mockIPC } from "@tauri-apps/api/mocks";
import { checkConnection, DEFAULT_API_URL, fetchApi } from "../src/connection";

const globals = globalThis as typeof globalThis & { isTauri?: boolean };
const originalWindow = Object.getOwnPropertyDescriptor(globalThis, "window");
const originalFlag = globals.isTauri;
afterEach(() => {
  clearMocks();
  if (originalWindow) Object.defineProperty(globalThis, "window", originalWindow);
  else Reflect.deleteProperty(globalThis, "window");
  globals.isTauri = originalFlag;
});

function nativeMock() {
  Object.defineProperty(globalThis, "window", { value: globalThis, configurable: true });
  globals.isTauri = true;
  const calls: { command: string; payload: unknown }[] = [];
  mockIPC((command, args) => {
    calls.push({ command, payload: args });
    const path = (args as { path: string }).path;
    const body = path === "/health" ? { status: "ok" } : path === "/openapi.json"
      ? { paths: { "/api/v1/intake/research-drafts": {}, "/api/v1/guide-maps": {}, "/api/v1/simulation-plans": {} } }
      : { run_id: "synthetic-test" };
    return { status: 200, body: JSON.stringify(body) };
  });
  return calls;
}

test("native requests use the scoped IPC command without forwarding headers or credentials", async () => {
  const calls = nativeMock();
  expect(await checkConnection(DEFAULT_API_URL)).toBe("ready");
  const response = await fetchApi(`${DEFAULT_API_URL}/api/v1/runs`, {
    method: "POST", body: '{"research_object_id":"synthetic"}',
    headers: { Authorization: "must-not-be-forwarded" }, credentials: "include",
  });
  expect(await response.json()).toEqual({ run_id: "synthetic-test" });
  expect(calls.at(-1)).toEqual({ command: "api_request", payload: {
    method: "POST", path: "/api/v1/runs", body: '{"research_object_id":"synthetic"}',
  } });
});

test("native transport rejects off-origin addresses, URL credentials and pre-aborted requests", async () => {
  const calls = nativeMock();
  for (const url of ["https://evil.example/health", `${DEFAULT_API_URL}/health?key=x`, "https://user:password@casaiprovenancelab.vercel.app/health"]) {
    await expect(fetchApi(url)).rejects.toThrow("approved");
  }
  const controller = new AbortController();
  controller.abort();
  await expect(fetchApi(`${DEFAULT_API_URL}/health`, { signal: controller.signal })).rejects.toThrow();
  expect(calls).toHaveLength(0);
});
