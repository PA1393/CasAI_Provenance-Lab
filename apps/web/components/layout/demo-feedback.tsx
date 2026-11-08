"use client";

import { useState } from "react";
import { usePathname } from "next/navigation";
import { saveFeedbackText } from "@casai/env";
import { buildDemoFeedback, DEMO_REVIEW_VERSION } from "../../lib/demo-feedback";

export function DemoFeedback() {
  const context = usePathname();
  const [category, setCategory] = useState("usability");
  const [expected, setExpected] = useState("");
  const [actual, setActual] = useState("");
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState("");
  const [reportText, setReportText] = useState("");
  const [reviewed, setReviewed] = useState<string[]>([]);
  function prepareReport() {
    return JSON.stringify(buildDemoFeedback({ category, expected, actual, context,
      platform: navigator.platform || "Unknown" }), null, 2);
  }
  return <details className="relative">
    <summary className="cursor-pointer rounded-lg border border-border px-3 py-2 text-xs font-semibold">Demo help &amp; feedback</summary>
    <div className="fixed inset-x-4 top-24 z-50 mt-2 max-h-[75vh] overflow-y-auto rounded-xl border border-border-strong bg-bg-card p-5 shadow-raised sm:absolute sm:inset-x-auto sm:right-0 sm:top-full sm:w-[28rem]">
      <h2 className="font-serif-display text-xl">Try the demo</h2>
      <ol className="mt-3 list-decimal space-y-2 pl-5 text-sm leading-5 text-text-secondary">
        <li>Open Add research → Use synthetic example. This demo does not require login.</li>
        <li>Review and save. A public PDB example is optional.</li>
        <li>Start a run using rule-based C → T or A → G, enter a label, confirm the interpretation, then Submit. Keep the API running; hosted mode also requires database access. Check the connection indicator for storage type.</li>
        <li>Inspect Summary, Provenance and 3D interaction. Public reference loading needs a separate click.</li>
        <li>After a run finishes, choose Export recorded data.</li>
      </ol>
      <fieldset className="mt-4 space-y-2 rounded-lg border border-border p-3">
        <legend className="px-1 text-sm font-semibold">Reviewer checklist · this session only</legend>
        {["Input name and sequence match the reviewed file", "Summary and edit positions match the recorded result", "3D controls respond without implying validated motion", "Provenance shows completed or stopped stages", "Export JSON opens and feedback can be prepared"].map(item => <label key={item} className="flex items-start gap-2 text-xs leading-5"><input type="checkbox" checked={reviewed.includes(item)} onChange={event => setReviewed(values => event.target.checked ? [...values, item] : values.filter(value => value !== item))} className="mt-1" />{item}</label>)}
        <p className="text-xs text-muted">{reviewed.length}/5 checked by you. Not automated verification or scientific validation. Use the feedback fields below to report problems.</p>
      </fieldset>
      <p className="mt-3 text-xs text-muted">{DEMO_REVIEW_VERSION} · Use public/synthetic inputs. Rules and heuristic scores demonstrate software behavior; the 3D scene is illustrative. AI-assisted objectives are a separate mode.</p>
      <form className="mt-5 space-y-3 border-t border-border pt-4" onSubmit={async event => {
        event.preventDefault(); if (busy) return;
        setBusy(true); setNotice("");
        try {
          const result = await saveFeedbackText("casai-demo-feedback.json", prepareReport());
          setNotice(result === "cancelled" ? "Save cancelled." : result === "saved" ? "Feedback saved. Share the file with your reviewer when ready." : "Feedback download requested. Share the file with your reviewer when ready.");
        } catch { setNotice("Feedback could not be saved. Check the descriptions and choose a new filename. If saving was interrupted, inspect the selected file."); }
        finally { setBusy(false); }
      }}>
        <h3 className="font-semibold">Save feedback for review</h3>
        <p className="text-xs leading-5 text-muted">This downloads a report; nothing is sent automatically. It includes your text, screen/record ID, platform and demo version. No sequences or run payloads are automatically included. Leave credentials and private data out.</p>
        <label className="block text-sm">Area<select disabled={busy} value={category} onChange={event => { setCategory(event.target.value); setReportText(""); }} className="mt-1 w-full rounded border border-border bg-bg p-2">{["usability", "input", "run", "viewer", "export", "other"].map(value => <option key={value} value={value}>{value}</option>)}</select></label>
        <label className="block text-sm">Expected behavior<textarea disabled={busy} maxLength={2000} value={expected} onChange={event => { setExpected(event.target.value); setReportText(""); }} rows={2} className="mt-1 w-full rounded border border-border bg-bg p-2" /></label>
        <label className="block text-sm">What happened<textarea disabled={busy} required maxLength={2000} value={actual} onChange={event => { setActual(event.target.value); setReportText(""); }} rows={3} className="mt-1 w-full rounded border border-border bg-bg p-2" /></label>
        <button disabled={busy || !actual.trim()} className="rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-bg disabled:opacity-40">{busy ? "Saving…" : "Save feedback report"}</button>
        <button type="button" disabled={busy || !actual.trim()} className="ml-2 rounded-lg border border-border px-3 py-2 text-sm disabled:opacity-40" onClick={() => {
          try { setReportText(prepareReport()); } catch { setNotice("Check the feedback fields first."); }
        }}>Show report text</button>
        {reportText && <label className="block text-sm">Feedback JSON · copy manually if downloads are blocked<textarea readOnly rows={6} value={reportText} className="mt-1 w-full rounded border border-border bg-bg p-2 font-mono text-xs" /></label>}
        {notice && <p role="status" className="text-sm">{notice}</p>}
      </form>
    </div>
  </details>;
}
