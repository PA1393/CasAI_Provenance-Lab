"use client";

import { useState } from "react";
import { ConfirmedInputActions } from "./confirmed-input-actions";
import { confirmIntakeDraft, inspectDatasetText, resumeIntakeDraft, storeIntakeDraft } from "@/lib/api/client";
import { confirmationBody, INPUT_BYTE_LIMIT, validateTextInput, type IntakeMethod, type StoredDraft, type DatasetInspection } from "@/lib/intake";

const field = "mt-1 w-full rounded-lg border border-border bg-bg-card p-3 text-sm";
const button = "rounded-lg border border-border px-4 py-2 text-sm font-semibold disabled:opacity-40";
const methods: [IntakeMethod | "fastq" | "vcf", string][] = [["fasta", "FASTA draft"], ["pasted_sequence", "Paste sequence"], ["demo", "Synthetic example"], ["accession", "Accession request"], ["gene", "Gene request"], ["objective", "Research objective"], ["fastq", "FASTQ evidence"], ["vcf", "VCF evidence"]];

export function ProcessorPanel() {
  const [method, setMethod] = useState<(typeof methods)[number][0]>("pasted_sequence");
  const [content, setContent] = useState("");
  const [filename, setFilename] = useState("input.fastq");
  const [molecule, setMolecule] = useState("DNA");
  const [convert, setConvert] = useState(false);
  const [phred33, setPhred33] = useState(false);
  const [accession, setAccession] = useState("");
  const [organism, setOrganism] = useState("");
  const [transcript, setTranscript] = useState("");
  const [assembly, setAssembly] = useState("");
  const [reference, setReference] = useState("");
  const [actor, setActor] = useState("");
  const [ack, setAck] = useState(false);
  const [draft, setDraft] = useState<StoredDraft | null>(null);
  const [dataset, setDataset] = useState<DatasetInspection | null>(null);
  const [version, setVersion] = useState("");
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState("");
  const evidence = method === "fastq" || method === "vcf";
  function invalidate() { setDraft(null); setDataset(null); setVersion(""); setAck(false); setNotice(""); }
  async function action(operation: () => Promise<void>) {
    setBusy(true); setNotice("");
    try { await operation(); } catch (error) { setNotice(error instanceof Error ? error.message : "Request failed. Nothing was confirmed."); }
    finally { setBusy(false); }
  }
  async function inspect() {
    invalidate();
    if (evidence) {
      validateTextInput(content);
      const result = await inspectDatasetText({ declared_format: method, content, filename,
        ...(method === "vcf" && assembly.trim() ? { reference_assembly: assembly.trim() } : {}),
        ...(method === "vcf" && reference.trim() ? { reference_content: reference } : {}),
        ...(method === "fastq" && phred33 ? { quality_encoding: "phred33" } : {}) });
      setDataset(result); return;
    }
    if (["fasta", "pasted_sequence", "objective"].includes(method)) validateTextInput(content);
    const result = await storeIntakeDraft({ input_method: method,
      molecule_type: method === "demo" ? "DNA" : molecule,
      rna_to_dna: method !== "demo" && molecule === "RNA" && convert,
      ...(["fasta", "pasted_sequence", "objective"].includes(method) ? { content } : {}),
      ...(method === "accession" ? { accession } : {}),
      ...(method === "gene" ? { gene_symbol: accession } : {}),
      ...(organism.trim() ? { organism: organism.trim() } : {}),
      ...(transcript.trim() ? { transcript: transcript.trim() } : {}),
      ...(assembly.trim() ? { reference_assembly: assembly.trim() } : {}) });
    setDraft(result);
    try { localStorage.setItem("casai-last-draft-id", result.draft_id); }
    catch { setNotice("Draft stored on the backend; copy its ID to resume. Local preference storage is unavailable."); }
  }
  const report = draft?.draft ?? dataset?.draft;
  return <section className="mt-8 rounded-xl border border-border bg-bg-card p-6" aria-label="Information Processor">
    <h2 className="font-serif-display text-2xl">Information Processor</h2>
    <p className="mt-2 text-sm text-text-secondary">Inspect additional input types or create an immutable sequence draft. Reads and variants are evidence, not executable target sequences. Accession/gene requests stay unresolved until exact reference data is supplied; no automatic downloads.</p>
    <fieldset disabled={busy} onChange={invalidate} className="mt-5 grid gap-4 sm:grid-cols-2">
      <label className="text-sm">Input method<select className={field} value={method} onChange={event => { setMethod(event.target.value as typeof method); setContent(""); setFilename(event.target.value === "vcf" ? "input.vcf" : "input.fastq"); }}>{methods.map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>
      {!evidence && <label className="text-sm">Molecule declaration<select className={field} value={molecule} onChange={event => { setMolecule(event.target.value); setConvert(false); }}><option>DNA</option><option>RNA</option><option value="protein">Protein</option></select></label>}
      {!evidence && molecule === "RNA" && <label className="text-sm"><input type="checkbox" checked={convert} onChange={event => setConvert(event.target.checked)} /> Explicitly convert RNA U → DNA T</label>}
      {method === "fastq" && <label className="text-sm"><input type="checkbox" checked={phred33} onChange={event => setPhred33(event.target.checked)} /> I declare Phred+33 quality encoding (otherwise unresolved)</label>}
      {method !== "demo" && method !== "accession" && method !== "gene" && <label className="text-sm sm:col-span-2">{evidence ? "Evidence file (uncompressed UTF-8, up to 10 MB)" : "Optional file, or paste below"}<input type="file" accept={method === "fastq" ? ".fastq,.fq" : method === "vcf" ? ".vcf" : ".fa,.fasta,.fna,.txt"} className={field} onChange={event => {
        const file = event.target.files?.[0]; if (!file) return;
        if (file.size > INPUT_BYTE_LIMIT) { setNotice("File exceeds 10 MB."); return; }
        void action(async () => { const text = await file.text(); validateTextInput(text); setContent(text); setFilename(file.name); });
      }} /></label>}
      {method !== "demo" && <label className="text-sm sm:col-span-2">{method === "accession" ? "Exact accession/version" : method === "gene" ? "Gene symbol" : method === "objective" ? "Objective (never converted into invented sequence)" : "Input text"}
        {method === "accession" || method === "gene" ? <input value={accession} onChange={event => setAccession(event.target.value)} className={field} /> : <textarea rows={5} value={content} onChange={event => setContent(event.target.value)} className={`${field} font-mono`} />}</label>}
      {!evidence && <><label className="text-sm">Organism<input className={field} value={organism} onChange={event => setOrganism(event.target.value)} /></label><label className="text-sm">Exact transcript/version<input className={field} value={transcript} onChange={event => setTranscript(event.target.value)} /></label></>}
      {method !== "fastq" && <label className="text-sm">Reference assembly/version<input className={field} value={assembly} onChange={event => setAssembly(event.target.value)} /></label>}
      {method === "vcf" && <label className="text-sm sm:col-span-2">Supplied reference FASTA (optional; needed for REF validation)<textarea rows={3} className={`${field} font-mono`} value={reference} onChange={event => setReference(event.target.value)} /></label>}
    </fieldset>
    <div className="mt-4 flex flex-wrap gap-3"><button className={button} disabled={busy} onClick={() => void action(inspect)}>{busy ? "Processing…" : evidence ? "Inspect evidence" : "Store and inspect draft"}</button>
      <button className={button} disabled={busy} onClick={() => void action(async () => {
        let id = ""; try { id = localStorage.getItem("casai-last-draft-id") ?? ""; } catch { /* no stored pointer */ }
        if (!id) throw new Error("No saved draft pointer on this device.");
        invalidate(); setDraft(await resumeIntakeDraft(id));
      })}>Resume last stored draft</button></div>
    {report && <div className="mt-5 space-y-3 rounded-lg bg-bg-sunken p-4 text-sm">
      {draft && <><p className="break-all">Draft ID: {draft.draft_id}</p><p className="break-all">Normalized checksum: {draft.draft.normalized_checksum}</p><ul>{draft.draft.records.map(record => <li key={record.record_id}>{record.record_id}: {record.sequence_length.toLocaleString()} bases/residues · {record.molecule_type ?? "undeclared"}</li>)}</ul><details><summary>Field origins</summary><ul>{Object.entries(draft.draft.field_origins ?? {}).map(([name, origin]) => <li key={name}>{name}: {origin}</li>)}</ul></details></>}
      {dataset && <p>{dataset.draft.record_count} {dataset.draft.data_role} records · Reference checked: {dataset.draft.reference_checked ? "yes" : "no"}. Inspection only; not stored or executable.</p>}
      {report.warnings.map(warning => <p key={warning.code}>{warning.code}: {warning.message}</p>)}
      {report.missing_fields.map(gap => <p key={gap.field}>{gap.requirement}: {gap.field} — {gap.reason} {gap.action}</p>)}
      {draft && <div className="space-y-3 border-t border-border pt-3"><label className="block">Reviewer attribution (not authentication)<input disabled={busy} className={field} value={actor} onChange={event => { setActor(event.target.value); setVersion(""); }} maxLength={200} /></label><label className="block"><input disabled={busy} type="checkbox" checked={ack} onChange={event => setAck(event.target.checked)} /> I reviewed the records and acknowledge the warnings above.</label><button className={button} disabled={busy || !draft.draft.ready_for_confirmation || !ack || !!version} onClick={() => void action(async () => {
        const confirmed = await confirmIntakeDraft(draft.draft_id, confirmationBody(draft.draft, actor, ack)); setVersion(confirmed.version_id);
      })}>Confirm immutable version</button><p>After confirmation, download your normalized records or explicitly prepare a supported DNA record for run setup.</p></div>}
      {version && <p role="status" className="break-all">Confirmed version: {version}</p>}
      {version && draft && <ConfirmedInputActions key={version} versionId={version} records={draft.draft.records} busy={busy} perform={action} onNotice={setNotice} />}
    </div>}
    {notice && <p role="status" className="mt-3 text-sm text-text-secondary">{notice}</p>}
    <p className="mt-4 text-xs text-muted">Inspect/Store sends the supplied content to the configured backend. Use only non-sensitive demo data. Backend local workspace storage must be persistent to resume after server restarts.</p>
  </section>;
}
