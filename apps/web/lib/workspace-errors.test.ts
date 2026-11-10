import assert from "node:assert/strict";
import { test } from "node:test";
import { ApiError } from "./api/errors";
test("missing schema is explained without treating an interrupted write as harmless", () => {
  const error = new ApiError(503, true, "workspace_setup_required");
  assert.match(error.message, /migration 009/);
  assert.match(error.message, /earlier writes may have been recorded/);
});
test("unknown upstream codes never expose error payloads", () => {
  assert(!new ApiError(503, false, "credential=private").message.includes("credential"));
});
