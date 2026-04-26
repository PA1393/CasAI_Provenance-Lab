import type { ResearchObject } from "@/lib/api/client";

type Props = {
  researchObject: ResearchObject;
};

export function ResearchObjectSummary({ researchObject }: Props) {
  const {
    research_object_id,
    created_at,
    name,
    pdb_id,
    input_filename,
    input_file_type,
    status,
    ro_hash,
    mmcif_fetched_from,
    sequence_length,
    gc_content,
    avg_phred_score,
    reads_passing_qc,
    reads_total,
  } = researchObject;

  return (
    <div className="rounded-3xl border border-slate-200/80 bg-white/85 p-6 shadow-sm">
      <dl className="grid gap-5 sm:grid-cols-2">
        <Field label="ID" value={research_object_id} mono />
        <Field label="Status" value={status} />
        <Field label="Name" value={name} />
        <Field label="PDB ID" value={pdb_id} mono />
        <Field label="Input File" value={input_filename} />
        <Field label="File Type" value={input_file_type} />
        <Field label="Hash" value={ro_hash} mono wide />
        {mmcif_fetched_from && <Field label="mmCIF Source" value={mmcif_fetched_from} wide />}
        {sequence_length != null && <Field label="Sequence Length" value={String(sequence_length)} />}
        {gc_content != null && <Field label="GC Content" value={gc_content.toFixed(2)} />}
        {avg_phred_score != null && <Field label="Avg Phred" value={avg_phred_score.toFixed(1)} />}
        {reads_passing_qc != null && <Field label="Reads Passing QC" value={reads_passing_qc.toLocaleString()} />}
        {reads_total != null && <Field label="Reads Total" value={reads_total.toLocaleString()} />}
        <Field label="Created" value={new Date(created_at).toLocaleString()} wide />
      </dl>
    </div>
  );
}

function Field({
  label,
  value,
  mono = false,
  wide = false,
}: {
  label: string;
  value: string;
  mono?: boolean;
  wide?: boolean;
}) {
  return (
    <div className={wide ? "sm:col-span-2" : ""}>
      <dt className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-400">
        {label}
      </dt>
      <dd className={`mt-1 break-all text-sm text-slate-700 ${mono ? "font-mono" : ""}`}>
        {value}
      </dd>
    </div>
  );
}
