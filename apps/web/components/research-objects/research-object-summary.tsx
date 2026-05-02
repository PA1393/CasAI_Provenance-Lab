import type { ResearchObject } from "@/lib/api/client";
import { Hash } from "@/components/ui/hash";

type Props = {
  researchObject: ResearchObject;
};

export function ResearchObjectSummary({ researchObject }: Props) {
  const {
    created_at,
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
    fasta_preview,
    target_region,
  } = researchObject;

  return (
    <div className="flex flex-col gap-4">

      {fasta_preview && (
        <div className="rounded-2xl border border-slate-200/80 bg-slate-50/60 px-5 py-4">
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-400">
            Sequence Preview
          </p>
          <p className="mt-2 break-all font-mono text-xs leading-relaxed text-slate-600">
            {fasta_preview}
          </p>
          {target_region && (
            <p className="mt-2 text-xs text-slate-400">
              Target region:{" "}
              <span className="font-mono text-accent">
                [{target_region[0]}–{target_region[1]}]
              </span>
            </p>
          )}
        </div>
      )}

      <div className="rounded-3xl border border-slate-200/80 bg-white/85 p-6 shadow-sm">
        <dl className="grid gap-5 sm:grid-cols-2">
          <Field label="Status" value={status} />
          <Field label="PDB ID" value={pdb_id} mono />
          <Field label="Input File" value={input_filename} />
          <Field label="File Type" value={input_file_type} />
          <div className="sm:col-span-2">
            <dt className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-400">
              Object Hash
            </dt>
            <dd className="mt-1">
              <Hash value={ro_hash} length={24} />
            </dd>
          </div>
          {mmcif_fetched_from && <Field label="mmCIF Source" value={mmcif_fetched_from} wide />}
          {sequence_length != null && (
            <Field label="Sequence Length" value={`${sequence_length.toLocaleString()} bp`} />
          )}
          {gc_content != null && (
            <Field label="GC Content" value={`${(gc_content * 100).toFixed(1)}%`} />
          )}
          {avg_phred_score != null && (
            <Field label="Avg Phred Score" value={avg_phred_score.toFixed(1)} />
          )}
          {reads_passing_qc != null && reads_total != null && (
            <Field
              label="Reads Passing QC"
              value={`${reads_passing_qc.toLocaleString()} / ${reads_total.toLocaleString()}`}
              wide
            />
          )}
          <Field label="Created" value={new Date(created_at).toLocaleString()} wide />
        </dl>
      </div>
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
