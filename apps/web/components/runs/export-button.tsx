"use client";

import { useState } from "react";
import { getRunExport } from "../../lib/api/client";
import { verifyDemoExport } from "../../lib/demo-export";
import { exportNotice } from "../../lib/export-notice";
import { saveExportText } from "@casai/env";
import { ApiError } from "../../lib/api/errors";

export function ExportButton({ runId, enabled }: { runId: string; enabled: boolean }) {
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState("");
  const [verified, setVerified] = useState("");
  const [showText, setShowText] = useState(false);
  async function download() {
    setBusy(true); setNotice(""); setVerified(""); setShowText(false);
    let saving = false;
    try {
      const content = await verifyDemoExport(await getRunExport(runId), runId);
      setVerified(content);
      saving = true;
      const result = await saveExportText(`casai-run-${runId.replace(/[^a-zA-Z0-9_-]/g, "")}.json`, content);
      setNotice(exportNotice(result, content.length <= 200_000));
      if (content.length <= 200_000 && (result === "requested" || result === "cancelled")) setShowText(true);
    } catch (caught) {
      if (saving) setShowText(true);
      setNotice(saving
        ? "Saving could not finish. Choose a new filename; existing files are not overwritten. If the save was interrupted, inspect the selected file before using it."
        : caught instanceof ApiError ? caught.message : "The export package could not be verified. Nothing was sent to the save dialog.");
    }
    finally { setBusy(false); }
  }
  return <div className="my-4 rounded-lg border border-border bg-bg-card p-4">
    <button type="button" onClick={() => void download()} disabled={!enabled || busy} className="rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-bg disabled:opacity-40">{busy ? "Verifying package…" : "Export recorded data"}</button>
    <p className="mt-2 text-xs text-muted">JSON snapshot · SHA-256 file checksums · unverified source rights · available after a run finishes</p>
    {verified && verified.length <= 200_000 && <button type="button" disabled={busy} onClick={() => setShowText(value => !value)} className="mt-3 text-sm text-accent underline">{showText ? "Hide verified JSON" : "Show verified JSON for manual copying"}</button>}
    {showText && verified.length <= 200_000 && <label className="mt-3 block text-sm">Verified run package · select and copy into a new .json file<textarea readOnly value={verified} rows={8} className="mt-2 w-full rounded border border-border bg-bg p-3 font-mono text-xs" /></label>}
    {notice && <p role="status" className="mt-2 text-sm text-text-secondary">{notice}</p>}
  </div>;
}
