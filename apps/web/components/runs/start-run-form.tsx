"use client";

import { useRouter } from "next/navigation";
import Link from "next/link";
import { useEffect, useState } from "react";
import { createRun, getDemoCapabilities } from "../../lib/api/client";
import { ApiError, submissionMayExist } from "../../lib/api/errors";
import { clarifyPrompt } from "../../lib/prompt-clarification";

type Props = {
  researchObjectId: string;
  initialOpen?: boolean;
};

export function StartRunForm({ researchObjectId, initialOpen = false }: Props) {
  const router = useRouter();
  const [open, setOpen] = useState(initialOpen);
  const [prompt, setPrompt] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [mode, setMode] = useState<"demo_cbe" | "demo_abe" | "assisted">("demo_cbe");
  const [compatible, setCompatible] = useState<boolean | null>(null);
  const [uncertain, setUncertain] = useState(false);
  const [confirmed, setConfirmed] = useState<string | null>(null);
  const clarification = clarifyPrompt(prompt, mode);
  const confirmationKey = JSON.stringify([researchObjectId, prompt.trim(), mode]);
  const accepted = confirmed === confirmationKey;
  useEffect(() => {
    if (!open) return;
    let active = true;
    getDemoCapabilities().then(value => { if (active) setCompatible(value); }, () => { if (active) setCompatible(false); });
    return () => { active = false; };
  }, [open]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (submitting || uncertain || compatible !== true || !prompt.trim() || !accepted) return;
    setSubmitting(true);
    setError(null);
    try {
      const run = await createRun({ research_object_id: researchObjectId, prompt: prompt.trim(), execution_mode: mode });
      router.push(`/runs/${run.run_id}`);
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "The run response was interrupted. Check Runs before submitting again.");
      setUncertain(submissionMayExist(caught));
      setSubmitting(false);
    }
  }

  if (!open) {
    return (
      <button
        onClick={() => setOpen(true)}
        className="font-mono text-xs tracking-[0.2em] uppercase font-semibold px-5 py-3 rounded border border-accent text-accent hover:bg-accent hover:text-bg transition-colors"
      >
        Start Run →
      </button>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-3 w-full max-w-sm">
      <label className="text-sm font-semibold">Run mode<select disabled={submitting || uncertain} value={mode} onChange={event => setMode(event.target.value as typeof mode)} className="mt-2 w-full rounded-lg border border-border bg-bg-card p-3">
        <option value="demo_cbe">Rule-based demo · C → T</option>
        <option value="demo_abe">Rule-based demo · A → G</option>
        <option value="assisted">AI-assisted objective</option>
      </select></label>
      <p className="text-xs leading-5 text-muted">{mode === "assisted" ? "Uses the configured AI/retrieval services to interpret your objective. Availability and interpretation can vary." : "Searches the full saved sequence for the first compatible NGG site and uses guide positions 4–8. No AI call. The label below names the run; it does not control the edit. Heuristic software demonstration only."}</p>
      {compatible !== true && <p role="status" className="text-xs text-accent-amber">{compatible === null ? "Checking demo support…" : "Demo support could not be verified. Refresh after updating the backend."}</p>}
      <label htmlFor="run-objective" className="text-sm font-semibold">{mode === "assisted" ? "Editing objective" : "Run label"}</label>
      <textarea
        id="run-objective"
        autoFocus
        disabled={submitting || uncertain}
        maxLength={2000}
        value={prompt}
        onChange={(e) => setPrompt(e.target.value)}
        placeholder={mode === "assisted" ? "Describe the intended base edit…" : "Example: Synthetic CBE review"}
        rows={4}
        className="w-full rounded-lg border border-border bg-bg-card px-4 py-3 text-sm text-text placeholder:text-muted focus:border-accent focus:outline-none resize-none transition-colors"
      />
      {clarification && <section aria-label="Confirm your intent" className="rounded-xl border border-border bg-bg-card p-4 text-sm">
        <p className="font-semibold">Are you looking for this?</p>
        <p className="mt-2 leading-6 text-text-secondary">{clarification.message}</p>
        {(clarification.conflict || clarification.requiresChoice) && <p className="mt-2 text-accent-amber">Your text mentions a different editor or both editors. Choose the intended run mode before confirming.</p>}
        <div className="mt-3 flex flex-wrap gap-3">
          <button type="button" disabled={submitting || uncertain || clarification.conflict || clarification.requiresChoice} onClick={() => setConfirmed(confirmationKey)} className="rounded border border-accent px-3 py-2 text-accent">{accepted ? "Confirmed" : "Yes, that's right"}</button>
          <button type="button" disabled={submitting || uncertain} onClick={() => { setConfirmed(null); setPrompt(""); document.getElementById("run-objective")?.focus(); }} className="rounded border border-border px-3 py-2">No, start again</button>
          <button type="button" disabled={submitting || uncertain} onClick={() => { setConfirmed(null); document.getElementById("run-objective")?.focus(); }} className="rounded border border-border px-3 py-2">Be more specific</button>
        </div>
        <p className="mt-3 text-xs text-muted">Rule-based clarification. Confirmation does not start the run; use Submit below.</p>
      </section>}
      {error && (
        <p role="alert" className="text-xs text-accent-amber">{error}</p>
      )}
      {uncertain && <Link href="/runs" className="text-sm text-accent underline">Inspect recorded runs before starting another</Link>}
      <div className="flex gap-2">
        <button
          type="submit"
          disabled={submitting || uncertain || compatible !== true || !prompt.trim() || !accepted}
          className="font-mono text-xs tracking-[0.2em] uppercase font-semibold px-5 py-3 rounded bg-accent text-bg hover:opacity-90 disabled:opacity-40 transition-opacity"
        >
          {submitting ? "Starting…" : "Submit"}
        </button>
        <button
          type="button"
          disabled={submitting || uncertain}
          onClick={() => {
            setOpen(false);
            setPrompt("");
            setError(null);
          }}
          className="font-mono text-xs tracking-[0.2em] uppercase font-semibold px-5 py-3 rounded border border-border text-muted hover:border-text hover:text-text transition-colors"
        >
          Cancel
        </button>
      </div>
    </form>
  );
}
