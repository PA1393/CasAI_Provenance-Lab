import { expect, test } from "bun:test";
import config from "../src-tauri/tauri.conf.json";
import { DEFAULT_API_URL } from "../src/connection";

test("release packages embed the client instead of requiring a localhost web server", () => {
  expect(config.build.frontendDist).toBe("../dist");
  expect(config.build.beforeBuildCommand).toBe("bun run build");
  expect(config.app.windows[0].useHttpsScheme).toBe(true);
  expect(config.app.windows[0].dragDropEnabled).toBe(false);
});

test("release CSP permits only local scripts and explicit API/structure origins", () => {
  const csp = config.app.security.csp;
  expect(csp).toContain(DEFAULT_API_URL);
  expect(csp).toContain("https://files.rcsb.org");
  expect(csp).toContain("script-src 'self' 'wasm-unsafe-eval'");
  expect(csp).not.toContain("'unsafe-eval'");
  expect(csp.split(/[;\s]+/)).not.toContain("https:");
  expect(csp).not.toContain("*");
  expect(csp).not.toContain("127.0.0.1:3000");
});
