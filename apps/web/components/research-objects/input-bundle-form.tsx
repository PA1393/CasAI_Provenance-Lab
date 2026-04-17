"use client";

import { useState } from "react";

export function InputBundleForm() {
  const [sequenceData, setSequenceData] = useState("");
  const [metaKey, setMetaKey] = useState("");
  const [metaValue, setMetaValue] = useState("");

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    // Placeholder — POST endpoint not yet implemented on the backend.
    alert("Submit not yet wired to backend.");
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="rounded-3xl border border-slate-200/80 bg-white/85 p-6 shadow-sm"
    >
      <div className="flex flex-col gap-5">
        <label className="flex flex-col gap-1.5">
          <span className="text-sm font-medium text-slate-700">Sequence data</span>
          <textarea
            value={sequenceData}
            onChange={(e) => setSequenceData(e.target.value)}
            rows={5}
            placeholder="Paste gene sequence here…"
            className="rounded-xl border border-slate-200 bg-mist px-4 py-3 font-mono text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-accent/40"
          />
        </label>

        <fieldset className="flex flex-col gap-2">
          <legend className="text-sm font-medium text-slate-700">
            Metadata (single key/value for now)
          </legend>
          <div className="grid grid-cols-2 gap-3">
            <input
              type="text"
              value={metaKey}
              onChange={(e) => setMetaKey(e.target.value)}
              placeholder="Key"
              className="rounded-xl border border-slate-200 bg-mist px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-accent/40"
            />
            <input
              type="text"
              value={metaValue}
              onChange={(e) => setMetaValue(e.target.value)}
              placeholder="Value"
              className="rounded-xl border border-slate-200 bg-mist px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-accent/40"
            />
          </div>
        </fieldset>
      </div>

      <button
        type="submit"
        className="mt-6 inline-flex rounded-full bg-ink px-6 py-2.5 text-sm font-semibold text-white transition hover:bg-slate-800"
      >
        Create Research Object
      </button>
    </form>
  );
}
