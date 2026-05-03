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
  const [targetStart, setTargetStart] = useState("");
  const [targetEnd, setTargetEnd] = useState("");
  const [showAdvanced, setShowAdvanced] = useState(false);
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
      const start = parseInt(targetStart);
      const end = parseInt(targetEnd);
      const target_region =
        targetStart && targetEnd && !isNaN(start) && !isNaN(end) && start < end
          ? [start, end]
          : undefined;

      const created = await createResearchObject({
        name,
        input_filename: inputFilename,
        input_file_type: inputFileType,
        pdb_id: pdbId,
        ...(target_region ? { target_region } : {}),
      });
      router.push(`/research-objects/${created.research_object_id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Submission failed.");
      setSubmitting(false);
    }
  }

  const inputBase =
    "w-full bg-bg-card border border-border rounded px-4 py-3 text-text font-sans focus:border-accent focus:outline-none transition-colors";

  return (
    <form
      onSubmit={handleSubmit}
      className="rounded-lg border border-border bg-bg-card p-6"
    >
      <div className="flex flex-col gap-5">
        <FormLabel label="NAME" required>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
            placeholder="e.g. BRCA2 base-edit trial"
            className={inputBase}
          />
        </FormLabel>

        <FormLabel label="INPUT FILE" required>
          <input
            type="file"
            onChange={handleFileChange}
            required
            className={`${inputBase} file:mr-4 file:py-1 file:px-3 file:rounded file:border-0 file:bg-border file:text-text file:font-mono file:text-xs file:cursor-pointer hover:file:bg-accent/20`}
          />
          {inputFilename && (
            <span className="font-mono text-xs text-muted mt-1 block">{inputFilename}</span>
          )}
        </FormLabel>

        <FormLabel label="FILE TYPE" required>
          <select
            value={inputFileType}
            onChange={(e) => setInputFileType(e.target.value)}
            className={inputBase}
          >
            <option value="fastq">FASTQ</option>
            <option value="fasta">FASTA</option>
            <option value="vcf">VCF</option>
            <option value="other">Other</option>
          </select>
        </FormLabel>

        <FormLabel label="PDB ID" required>
          <input
            type="text"
            value={pdbId}
            onChange={(e) => setPdbId(e.target.value.toUpperCase())}
            required
            maxLength={4}
            placeholder="e.g. 1ABC"
            className={inputBase}
          />
        </FormLabel>
      </div>

      {error && (
        <p className="mt-4 rounded-lg border border-accent-red/40 bg-bg px-4 py-3 font-mono text-xs text-accent-red">
          ERROR: {error}
        </p>
      )}

      <button
        type="submit"
        disabled={submitting}
        className="mt-6 inline-flex font-mono text-xs tracking-[0.2em] uppercase font-semibold px-6 py-3 rounded bg-text text-bg hover:bg-accent transition-colors disabled:opacity-50"
      >
        {submitting ? "Creating…" : "Create Research Object →"}
      </button>
    </form>
  );
}

function FormLabel({
  label,
  required,
  small,
  children,
}: {
  label: string;
  required?: boolean;
  small?: boolean;
  children: React.ReactNode;
}) {
  return (
    <label className={`flex flex-col gap-2 ${small ? "flex-1" : ""}`}>
      <span className="font-mono text-[10px] tracking-[0.2em] uppercase font-semibold text-muted">
        {label} {required && <span className="text-accent">*</span>}
      </span>
      {children}
    </label>
  );
}
