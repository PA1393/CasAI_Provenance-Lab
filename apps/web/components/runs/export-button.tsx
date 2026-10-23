"use client";

import { useState } from "react";
import { getRunExport } from "@/lib/api/client";
import { verifyDemoExport } from "@/lib/demo-export";
import { saveExportText } from "@casai/env";

export function ExportButton({ runId, enabled }: { runId: string; enabled: boolean }) {
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState("");
  async function download() {
    setBusy(true); setNotice("");
    try {
      const content = await verifyDemoExport(await getRunExport(runId), runId);
      const result = await saveExportText(`casai-run-${runId.replace(/[^a-zA-Z0-9_-]/g, "")}.json`, content);
      setNotice(result === "cancelled" ? "Save cancelled. No file was written." : result === "saved" ? "Checksums verified. Package saved to your chosen file." : "Checksums verified. Download requested; check your downloads.");
    } catch { setNotice("Export unavailable. Check backend compatibility and retry. No substitute or partial package was saved."); }
    finally { setBusy(false); }
  }
  return <div className="my-4 rounded-lg border border-border bg-bg-card p-4">
    <button type="button" onClick={() => void download()} disabled={!enabled || busy} className="rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-bg disabled:opacity-40">{busy ? "Verifying package…" : "Export recorded data"}</button>
    <p className="mt-2 text-xs text-muted">JSON snapshot · SHA-256 file checksums · unverified source rights · available after a run finishes</p>
    {notice && <p role="status" className="mt-2 text-sm text-text-secondary">{notice}</p>}
  </div>;
}
