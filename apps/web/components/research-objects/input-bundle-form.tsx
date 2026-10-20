"use client";

import { useRef, useState } from "react";
import { useRouter } from "next/navigation";

import { createResearchObject } from "@/lib/api/client";
import { parseTargetRegion } from "@/lib/uploads/target-region";
import {
  inspectFastaUpload,
  MAX_UPLOAD_BYTES,
  type FastaReview,
} from "@/lib/uploads/fasta-review";

type IntakeStep = "details" | "review";

function readFileText(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () =>
      typeof reader.result === "string"
        ? resolve(reader.result)
        : reject(new Error("File was not read as text"));
    reader.onerror = () => reject(reader.error ?? new Error("File could not be read"));
    reader.readAsText(file, "utf-8");
  });
}

export function InputBundleForm() {
  const router = useRouter();
  const fileInput = useRef<HTMLInputElement>(null);
  const inspectionId = useRef(0);
  const [step, setStep] = useState<IntakeStep>("details");
  const [name, setName] = useState("");
  const [pdbId, setPdbId] = useState("");
  const [targetStart, setTargetStart] = useState("");
  const [targetEnd, setTargetEnd] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [fastaText, setFastaText] = useState("");
  const [review, setReview] = useState<FastaReview | null>(null);
  const [reading, setReading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function inspectFile(selected: File | null) {
    const attempt = ++inspectionId.current;
    setStep("details");
    setFile(selected);
    setFastaText("");
    setReview(null);
    setError(null);
    setReading(false);
    if (!selected) return;

    if (selected.size > MAX_UPLOAD_BYTES) {
      setReview(inspectFastaUpload(selected.name, selected.size, ""));
      return;
    }

    setReading(true);
    try {
      const text = await readFileText(selected);
      if (attempt !== inspectionId.current) return;
      setFastaText(text);
      setReview(inspectFastaUpload(selected.name, selected.size, text));
    } catch {
      if (attempt !== inspectionId.current) return;
      setError("The selected file could not be read. Choose it again or use another file.");
    } finally {
      if (attempt === inspectionId.current) setReading(false);
    }
  }

  function targetRegion(): number[] | undefined {
    return parseTargetRegion(targetStart, targetEnd, review?.sequenceLength ?? 0);
  }

  function openReview(event: React.FormEvent) {
    event.preventDefault();
    setError(null);
    if (!file || !review?.ready) {
      setError("Choose a valid FASTA file before continuing.");
      return;
    }
    if (!/^[A-Z0-9]{4}$/.test(pdbId)) {
      setError("Enter a four-character PDB ID, such as 1ABC.");
      return;
    }
    try {
      targetRegion();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Check the target coordinates.");
      return;
    }
    setStep("review");
  }

  async function createObject() {
    if (!file || !review?.ready) return;
    setError(null);
    setSubmitting(true);
    try {
      const created = await createResearchObject({
        name: name.trim(),
        input_filename: file.name,
        input_file_type: "fasta",
        pdb_id: pdbId,
        fasta_text: fastaText,
        ...(targetRegion() ? { target_region: targetRegion() } : {}),
      });
      router.push(`/research-objects/${created.research_object_id}`);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "The research object was not created.");
      setSubmitting(false);
    }
  }

  if (step === "review" && file && review) {
    return (
      <section
        className="overflow-hidden rounded-xl border border-border-strong bg-bg-card"
        aria-labelledby="review-title"
      >
        <div className="grid border-b border-border bg-bg-sunken md:grid-cols-[1fr_auto] md:items-end">
          <div className="p-6 md:p-8">
            <p className="text-sm font-medium text-accent">Ready to create</p>
            <h2 id="review-title" className="mt-2 font-serif-display text-3xl">
              Review research input
            </h2>
            <p className="mt-3 max-w-2xl text-sm leading-6 text-text-secondary">
              Check the source and coordinates before saving the research input.
            </p>
          </div>
          <div className="border-t border-border px-6 py-5 md:border-l md:border-t-0 md:px-8">
            <p className="text-xs text-muted">Upload behavior</p>
            <p className="mt-1 font-medium">Sent only after confirmation</p>
          </div>
        </div>

        <div className="grid md:grid-cols-[minmax(0,1fr)_17rem]">
          <div className="min-w-0 p-6 md:p-8">
            <p className="text-sm font-semibold">{name.trim()}</p>
            <p className="mt-1 break-all text-sm text-text-secondary">{file.name}</p>
            <div className="mt-6 rounded-lg bg-bg-sunken p-4">
              <p className="mb-3 text-xs font-medium text-muted">Normalized sequence preview</p>
              <code className="block break-all text-sm leading-7 text-text">{review.preview}</code>
            </div>
            {review.issues.map((issue) => (
              <p key={issue.message} className="mt-4 text-sm text-accent-amber">
                {issue.message}
              </p>
            ))}
          </div>
          <dl className="grid grid-cols-2 border-t border-border bg-bg-sunken/60 p-6 md:block md:border-l md:border-t-0 md:p-8">
            <ReviewFact label="Format" value="FASTA" />
            <ReviewFact label="Sequence" value={`${review.sequenceLength.toLocaleString()} bp`} />
            <ReviewFact label="GC content" value={`${(review.gcContent * 100).toFixed(1)}%`} />
            <ReviewFact label="Records" value={review.recordCount.toString()} />
            <ReviewFact label="Ambiguous bases" value={review.ambiguousBases.toLocaleString()} />
            <ReviewFact label="PDB structure" value={pdbId} />
            {targetRegion() && (
              <ReviewFact label="Target window" value={`${targetStart}–${targetEnd}`} />
            )}
          </dl>
        </div>

        {error && <ErrorMessage message={error} />}
        <div className="flex flex-col-reverse gap-3 border-t border-border p-6 sm:flex-row sm:justify-end md:px-8">
          <button
            type="button"
            onClick={() => setStep("details")}
            disabled={submitting}
            className="rounded-lg border border-border-strong px-5 py-3 text-sm font-semibold hover:bg-bg-sunken disabled:opacity-50"
          >
            Back to edit
          </button>
          <button
            type="button"
            onClick={createObject}
            disabled={submitting}
            className="rounded-lg bg-text px-5 py-3 text-sm font-semibold text-bg hover:bg-accent disabled:opacity-50"
          >
            {submitting ? "Creating record…" : "Create research object"}
          </button>
        </div>
      </section>
    );
  }

  return (
    <form
      onSubmit={openReview}
      className="overflow-hidden rounded-xl border border-border-strong bg-bg-card"
    >
      <div className="grid border-b border-border md:grid-cols-[minmax(0,1fr)_15rem]">
        <div className="p-6 md:p-8">
          <label htmlFor="sequence-file" className="text-sm font-semibold">
            Sequence source
          </label>
          <p className="mt-1 text-sm leading-6 text-text-secondary">
            FASTA, FA, or FNA · up to 10 MB
          </p>
          <input
            ref={fileInput}
            id="sequence-file"
            type="file"
            accept=".fasta,.fa,.fna"
            onChange={(event) => void inspectFile(event.target.files?.[0] ?? null)}
            className="sr-only"
          />
          <button
            type="button"
            onClick={() => fileInput.current?.click()}
            onDragOver={(event) => event.preventDefault()}
            onDrop={(event) => {
              event.preventDefault();
              void inspectFile(event.dataTransfer.files[0] ?? null);
            }}
            className="mt-5 w-full rounded-lg border border-dashed border-border-strong bg-bg-sunken px-5 py-12 text-center hover:border-accent"
          >
            <span className="block font-medium">
              {file ? file.name : "Drop a FASTA file here or click to choose"}
            </span>
            <span className="mt-2 block text-sm text-muted">
              {reading
                ? "Reading locally…"
                : file
                  ? `${(file.size / 1000).toLocaleString()} KB selected`
                  : "The file stays in your browser until you create the record."}
            </span>
          </button>
        </div>
        <div className="border-t border-border bg-bg-sunken/60 p-6 md:border-l md:border-t-0 md:p-8">
          <p className="text-xs font-medium text-muted">Intake check</p>
          <p
            className={`mt-2 text-sm font-semibold ${review?.ready ? "text-accent" : "text-text-secondary"}`}
          >
            {reading
              ? "Inspecting file"
              : review?.ready
                ? "Sequence is valid"
                : review
                  ? "Needs attention"
                  : "Waiting for file"}
          </p>
          {review && (
            <p className="mt-3 text-sm leading-6 text-text-secondary">
              {review.sequenceLength.toLocaleString()} bp ·{" "}
              {(review.gcContent * 100).toFixed(1)}% GC
            </p>
          )}
        </div>
      </div>

      {review?.ready && <div className="grid gap-6 p-6 md:grid-cols-2 md:p-8">
        <Field label="Research object name" htmlFor="object-name">
          <input
            id="object-name"
            value={name}
            onChange={(event) => setName(event.target.value)}
            required
            placeholder="Analysis 01"
            className={inputClass}
          />
        </Field>
        <Field label="PDB structure ID" htmlFor="pdb-id" hint="Four letters or numbers">
          <input
            id="pdb-id"
            value={pdbId}
            onChange={(event) => setPdbId(event.target.value.toUpperCase())}
            required
            maxLength={4}
            placeholder="1ABC"
            className={inputClass}
          />
        </Field>
        <fieldset className="md:col-span-2">
          <legend className="text-sm font-semibold">
            Target window <span className="font-normal text-muted">(optional)</span>
          </legend>
          <p className="mt-1 text-sm text-text-secondary">
            Use 1-based inclusive coordinates. Leave both fields empty to review the full sequence.
          </p>
          <div className="mt-3 grid gap-3 sm:grid-cols-2">
            <input
              aria-label="Target start"
              inputMode="numeric"
              min="1"
              type="number"
              value={targetStart}
              onChange={(event) => setTargetStart(event.target.value)}
              placeholder="Start"
              className={inputClass}
            />
            <input
              aria-label="Target end"
              inputMode="numeric"
              min="1"
              type="number"
              value={targetEnd}
              onChange={(event) => setTargetEnd(event.target.value)}
              placeholder="End"
              className={inputClass}
            />
          </div>
        </fieldset>
      </div>}

      {review?.issues.map((issue) => (
        <ErrorMessage
          key={issue.message}
          message={issue.message}
          warning={issue.severity === "warning"}
        />
      ))}
      {error && <ErrorMessage message={error} />}
      <div className="flex items-center justify-between gap-4 border-t border-border px-6 py-5 md:px-8">
        <p className="text-xs leading-5 text-muted">
          Nothing is uploaded until you save the reviewed input.
        </p>
        <button
          type="submit"
          disabled={reading || !review?.ready}
          className="shrink-0 rounded-lg bg-text px-5 py-3 text-sm font-semibold text-bg hover:bg-accent disabled:cursor-not-allowed disabled:opacity-40"
        >
          Review upload
        </button>
      </div>
    </form>
  );
}

const inputClass =
  "mt-2 w-full rounded-lg border border-border-strong bg-bg-card px-4 py-3 text-text placeholder:text-muted focus:border-accent focus:outline-none";

function Field({
  label,
  htmlFor,
  hint,
  children,
}: {
  label: string;
  htmlFor: string;
  hint?: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <label htmlFor={htmlFor} className="text-sm font-semibold">
        {label}
      </label>
      {hint && <span className="ml-2 text-xs text-muted">{hint}</span>}
      {children}
    </div>
  );
}

function ReviewFact({ label, value }: { label: string; value: string }) {
  return (
    <div className="mb-5">
      <dt className="text-xs text-muted">{label}</dt>
      <dd className="mt-1 text-sm font-semibold text-text">{value}</dd>
    </div>
  );
}

function ErrorMessage({ message, warning = false }: { message: string; warning?: boolean }) {
  return (
    <p
      role={warning ? "status" : "alert"}
      className={`border-t border-border px-6 py-3 text-sm md:px-8 ${warning ? "bg-bg-sunken text-accent-amber" : "bg-accent-red/10 text-accent-red"}`}
    >
      {message}
    </p>
  );
}
