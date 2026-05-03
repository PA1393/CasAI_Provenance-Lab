import { existsSync } from "node:fs";
import { join } from "node:path";

const repoRoot = process.cwd();
const apiRoot = join(repoRoot, "apps", "api");
const pythonPath =
  process.platform === "win32"
    ? join(apiRoot, ".venv", "Scripts", "python.exe")
    : join(apiRoot, ".venv", "bin", "python");

if (!existsSync(pythonPath)) {
  console.error(`Backend virtual environment not found at ${pythonPath}`);
  console.error("Create it with:");
  console.error("  cd apps/api");
  console.error("  python -m venv .venv");
  console.error("  python -m pip install -e .[dev]");
  process.exit(1);
}

const proc = Bun.spawn([pythonPath, ...process.argv.slice(2)], {
  cwd: apiRoot,
  stdin: "inherit",
  stdout: "inherit",
  stderr: "inherit",
});

const exitCode = await proc.exited;
process.exit(exitCode);
