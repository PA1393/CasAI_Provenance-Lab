import { test, afterEach } from "node:test";
import assert from "node:assert/strict";
import { clarifyPrompt } from "./prompt-clarification";
import { setSession, getSession, accessToken } from "./auth-session";
import { getRuns, signIn, signOut } from "./api/client";

const original = globalThis.fetch;
afterEach(() => { setSession(null); globalThis.fetch = original; });
test("clarification distinguishes label/rule mode, conflicts and assisted uncertainty", () => {
  assert.equal(clarifyPrompt("", "demo_cbe"), null);
  assert(clarifyPrompt("use ABE", "demo_cbe")?.conflict);
  assert(clarifyPrompt("C to T", "demo_abe")?.conflict);
  assert(clarifyPrompt("CBE and ABE", "demo_cbe")?.requiresChoice);
  assert.match(clarifyPrompt("rice test", "demo_cbe")!.message, /run label/);
  assert.match(clarifyPrompt("rice test", "assisted")!.message, /not a validated/);
});
test("sign-in retains only the allowlisted user session, not cookies", async () => {
  globalThis.fetch = (async (_, init) => {
    assert.equal(init?.credentials, "omit");
    return Response.json({ access_token: "user-token", expires_in: 3600, user: { id: "one", email: "a@example.test" } });
  }) as typeof fetch;
  await signIn("a@example.test", "not-a-real-password");
  assert.equal(accessToken(), "user-token");
});
test("user token is forwarded and expired/invalid session clears workspace", async () => {
  setSession({ access_token: "user-token", expires_in: 3600, user: { id: "one", email: "" } });
  globalThis.fetch = (async (_, init) => {
    assert.equal(new Headers(init?.headers).get("Authorization"), "Bearer user-token");
    return Response.json({}, { status: 401 });
  }) as typeof fetch;
  await assert.rejects(getRuns());
  assert.equal(getSession(), null);
});
test("a late response cannot log out the next account or deliver the previous data", async () => {
  setSession({ access_token: "one", expires_in: 3600, user: { id: "one", email: "" } });
  globalThis.fetch = (async () => {
    setSession({ access_token: "two", expires_in: 3600, user: { id: "two", email: "" } });
    return Response.json({}, { status: 401 });
  }) as typeof fetch;
  await assert.rejects(getRuns());
  assert.equal(getSession()?.user.id, "two");
});
test("sign-out removes local access even if the remote logout fails", async () => {
  setSession({ access_token: "user-token", expires_in: 3600, user: { id: "one", email: "" } });
  globalThis.fetch = (async (_, init) => {
    assert.equal(getSession(), null);
    assert.equal(new Headers(init?.headers).get("Authorization"), "Bearer user-token");
    throw new TypeError("offline");
  }) as typeof fetch;
  await assert.rejects(signOut());
  assert.equal(getSession(), null);
});
