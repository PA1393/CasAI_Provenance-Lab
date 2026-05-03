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
        className="font-mono text-xs tracking-[0.2em] uppercase font-semibold px-5 py-3 rounded border border-accent text-accent hover:bg-accent hover:text-bg transition-colors"
      >
        Start Run →
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
        className="w-full rounded-lg border border-border bg-bg-card px-4 py-3 text-sm text-text placeholder:text-muted focus:border-accent focus:outline-none resize-none transition-colors"
      />
      {error && (
        <p className="font-mono text-xs text-accent-red">ERROR: {error}</p>
      )}
      <div className="flex gap-2">
        <button
          type="submit"
          disabled={submitting || !prompt.trim()}
          className="font-mono text-xs tracking-[0.2em] uppercase font-semibold px-5 py-3 rounded bg-accent text-bg hover:opacity-90 disabled:opacity-40 transition-opacity"
        >
          {submitting ? "Starting…" : "Submit"}
        </button>
        <button
          type="button"
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
