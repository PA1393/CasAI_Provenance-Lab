import { expect, test } from "bun:test";
import { runInNewContext } from "node:vm";
import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
import { molstarFrozenPrototype } from "../src/compat/molstar-frozen-prototype";
import config from "../src-tauri/tauri.conf.json";

test("Mol* namespace methods work with the desktop's frozen Object prototype", () => {
  const source = "const IntTuple = {};\nIntTuple.toString = String;\nIntTuple.toString(12)";
  expect(() => runInNewContext('"use strict"; Object.freeze(Object.prototype);' + source)).toThrow();
  const fixed = molstarFrozenPrototype(source, "/node_modules/molstar/lib/mol-data/int/tuple.js")!;
  expect(runInNewContext('"use strict"; Object.freeze(Object.prototype);' + fixed)).toBe("12");
  expect(config.app.security.freezePrototype).toBe(true);
});

test("transform matches the actual installed Mol* module, not application code", () => {
  const path = createRequire(new URL("../../web/package.json", import.meta.url)).resolve("molstar/lib/mol-data/int/tuple.js");
  const source = readFileSync(path, "utf8");
  expect(molstarFrozenPrototype(source, path)).toContain('__casaiDefineFrozenOwn(IntTuple, "toString"');
  expect(molstarFrozenPrototype(source, "/src/user-code.js")).toBeNull();
  expect(molstarFrozenPrototype("// thing.toString = arbitrary();", path)).toBeNull();
});

test("Immutable prototype methods retain assignment values without changing frozen globals", () => {
  const source = 'function Example() {}\nExample.prototype = {};\nconst assigned = (Example.prototype.constructor = Example);\nExample.prototype.toString = function () { return "ok"; };\n[assigned === Example, new Example().toString(), Object.isFrozen(Object.prototype)]';
  const fixed = molstarFrozenPrototype(source, "/node_modules/immutable/dist/immutable.js")!;
  expect(Array.from(runInNewContext('"use strict"; Object.freeze(Object.prototype);' + fixed))).toEqual([true, "ok", true]);
});

test("actual Immutable collection dependency initializes with the prototype freeze intact", () => {
  const molstarPath = createRequire(new URL("../../web/package.json", import.meta.url)).resolve("molstar/lib/mol-data/int/tuple.js");
  const path = createRequire(molstarPath).resolve("immutable");
  const fixed = molstarFrozenPrototype(readFileSync(path, "utf8"), path)!;
  expect(fixed).not.toBeNull();
  const module = { exports: {} };
  const result = runInNewContext('"use strict"; Object.freeze(Object.prototype);' + fixed + '\nmodule.exports.List([1, 2]).toString()', { module, exports: module.exports });
  expect(result).toBe("List [ 1, 2 ]");
});
