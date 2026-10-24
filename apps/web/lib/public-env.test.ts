import { test } from "node:test";
import assert from "node:assert/strict";
import { getPublicEnv } from "../../../packages/env/src/index";

test("public URL validation retains default, explicit URL and rejection behavior after Zod update", () => {
  const previous = process.env.NEXT_PUBLIC_API_BASE_URL;
  try {
    delete process.env.NEXT_PUBLIC_API_BASE_URL;
    assert.equal(getPublicEnv().NEXT_PUBLIC_API_BASE_URL, "http://127.0.0.1:8000");
    process.env.NEXT_PUBLIC_API_BASE_URL = "https://example.org";
    assert.equal(getPublicEnv().NEXT_PUBLIC_API_BASE_URL, "https://example.org");
    process.env.NEXT_PUBLIC_API_BASE_URL = "not-an-absolute-url";
    assert.throws(() => getPublicEnv());
  } finally {
    if (previous === undefined) delete process.env.NEXT_PUBLIC_API_BASE_URL;
    else process.env.NEXT_PUBLIC_API_BASE_URL = previous;
  }
});
