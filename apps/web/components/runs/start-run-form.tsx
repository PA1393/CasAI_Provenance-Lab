"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { createRun } from "@/lib/api/client";

type Props = {
  researchObjectId: string;
};

export function StartRunForm({ researchObjectId }: Props) {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [prompt, setPrompt] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!prompt.trim()) return;
    setSubmitting(true);
    setError(null);
    try {
      const run = await createRun({ research_object_id: researchObjectId, prompt });
      router.push(`/runs/${run.run_id}`);
    } catch {
      setError("Failed to start run. Please try again.");
      setSubmitting(false);
    }
  }

  if (!open) {
    return (
      <button
        onClick={() => setOpen(true)}
        className="inline-flex rounded-full border border-accent px-5 py-2.5 text-sm font-semibold text-accent transition hover:bg-accentSoft"
      >
        Start Run
      </button>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-3 w-full max-w-sm">
      <textarea
        autoFocus
        value={prompt}
        onChange={(e) => setPrompt(e.target.value)}
        placeholder="Describe what you want to run…"
        rows={4}
        className="w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-700 placeholder-slate-400 focus:border-accent focus:outline-none resize-none"
      />
      {error && <p className="text-xs text-red-500">{error}</p>}
      <div className="flex gap-2">
        <button
          type="submit"
          disabled={submitting || !prompt.trim()}
          className="inline-flex rounded-full border border-accent bg-accent px-5 py-2.5 text-sm font-semibold text-white transition hover:opacity-90 disabled:opacity-40"
        >
          {submitting ? "Starting…" : "Submit"}
        </button>
        <button
          type="button"
          onClick={() => { setOpen(false); setPrompt(""); setError(null); }}
          className="inline-flex rounded-full border border-slate-200 px-5 py-2.5 text-sm font-semibold text-slate-500 transition hover:border-slate-300"
        >
          Cancel
        </button>
      </div>
    </form>
  );
}
