"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { createResearchObject } from "@/lib/api/client";

export function InputBundleForm() {
  const router = useRouter();
  const [name, setName] = useState("");
  const [inputFilename, setInputFilename] = useState("");
  const [inputFileType, setInputFileType] = useState("fastq");
  const [pdbId, setPdbId] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (file) setInputFilename(file.name);
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const created = await createResearchObject({
        name,
        input_filename: inputFilename,
        input_file_type: inputFileType,
        pdb_id: pdbId,
      });
      router.push(`/research-objects/${created.research_object_id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Submission failed.");
      setSubmitting(false);
    }
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="rounded-3xl border border-slate-200/80 bg-white/85 p-6 shadow-sm"
    >
      <div className="flex flex-col gap-5">
        <label className="flex flex-col gap-1.5">
          <span className="text-sm font-medium text-slate-700">Name</span>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
            placeholder="e.g. BRCA2 base-edit trial"
            className="rounded-xl border border-slate-200 bg-mist px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-accent/40"
          />
        </label>

        <label className="flex flex-col gap-1.5">
          <span className="text-sm font-medium text-slate-700">Input file</span>
          <input
            type="file"
            onChange={handleFileChange}
            required
            className="rounded-xl border border-slate-200 bg-mist px-4 py-2.5 text-sm text-slate-700 focus:outline-none focus:ring-2 focus:ring-accent/40"
          />
          {inputFilename && (
            <span className="font-mono text-xs text-slate-400">{inputFilename}</span>
          )}
        </label>

        <label className="flex flex-col gap-1.5">
          <span className="text-sm font-medium text-slate-700">File type</span>
          <select
            value={inputFileType}
            onChange={(e) => setInputFileType(e.target.value)}
            className="rounded-xl border border-slate-200 bg-mist px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-accent/40"
          >
            <option value="fastq">FASTQ</option>
            <option value="fasta">FASTA</option>
            <option value="vcf">VCF</option>
            <option value="other">Other</option>
          </select>
        </label>

        <label className="flex flex-col gap-1.5">
          <span className="text-sm font-medium text-slate-700">PDB ID</span>
          <input
            type="text"
            value={pdbId}
            onChange={(e) => setPdbId(e.target.value.toUpperCase())}
            required
            maxLength={4}
            placeholder="e.g. 1ABC"
            className="w-28 rounded-xl border border-slate-200 bg-mist px-4 py-2.5 font-mono text-sm uppercase focus:outline-none focus:ring-2 focus:ring-accent/40"
          />
        </label>
      </div>

      {error && (
        <p className="mt-4 rounded-xl bg-red-50 px-4 py-2.5 text-sm text-red-600">{error}</p>
      )}

      <button
        type="submit"
        disabled={submitting}
        className="mt-6 inline-flex rounded-full bg-ink px-6 py-2.5 text-sm font-semibold text-white transition hover:bg-slate-800 disabled:opacity-50"
      >
        {submitting ? "Creating…" : "Create Research Object"}
      </button>
    </form>
  );
}
