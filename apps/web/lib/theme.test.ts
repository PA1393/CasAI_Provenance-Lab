import assert from "node:assert/strict";
import { test } from "node:test";
import { runInNewContext } from "node:vm";
import { resolveTheme, THEME_BOOTSTRAP } from "./theme";

test("appearance follows the OS unless the user saved a valid preference", () => {
  assert.equal(resolveTheme(null, true), "dark");
  assert.equal(resolveTheme(null, false), "light");
  assert.equal(resolveTheme("light", true), "light");
  assert.equal(resolveTheme("dark", false), "dark");
  assert.equal(resolveTheme("invalid", true), "dark");
});

test("pre-paint script respects OS, stored overrides and denied storage", () => {
  for (const [saved, systemDark, denied, expected] of [
    [null, true, false, "dark"], [null, false, false, "light"],
    ["light", true, false, "light"], ["dark", false, false, "dark"],
    [null, true, true, "dark"],
  ] as const) {
    const document = { documentElement: { dataset: {} as { theme?: string } } };
    runInNewContext(THEME_BOOTSTRAP, {
      document,
      window: { matchMedia: () => ({ matches: systemDark }) },
      localStorage: { getItem: () => { if (denied) throw new Error("denied"); return saved; } },
    });
    assert.equal(document.documentElement.dataset.theme, expected);
  }
});
