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
        <div className="rounded-lg border border-border bg-bg-card px-5 py-4">
          <p className="font-mono text-[10px] tracking-[0.2em] uppercase text-muted font-semibold">
            ──── SEQUENCE PREVIEW
          </p>
          <p className="mt-3 break-all font-mono text-xs leading-relaxed text-text">
            {fasta_preview}
          </p>
          {target_region && (
            <p className="mt-3 font-mono text-xs text-muted">
              Target region:{" "}
              <span className="text-accent">
                [{target_region[0]}–{target_region[1]}]
              </span>
            </p>
          )}
        </div>
      )}

      <div className="rounded-lg border border-border bg-bg-card p-6">
        <dl className="grid gap-5 sm:grid-cols-2">
          <Field label="STATUS" value={status} accent />
          <Field label="PDB ID" value={pdb_id} mono />
          <Field label="INPUT FILE" value={input_filename} />
          <Field label="FILE TYPE" value={input_file_type} mono />
          <div className="sm:col-span-2">
            <dt className="font-mono text-[10px] tracking-[0.2em] uppercase text-muted font-semibold">
              OBJECT HASH
            </dt>
            <dd className="mt-2">
              <Hash value={ro_hash} length={48} />
            </dd>
          </div>
          {mmcif_fetched_from && <Field label="MMCIF SOURCE" value={mmcif_fetched_from} wide mono />}
          {sequence_length != null && (
            <Field label="SEQUENCE LENGTH" value={`${sequence_length.toLocaleString()} bp`} mono />
          )}
          {gc_content != null && (
            <Field label="GC CONTENT" value={`${(gc_content * 100).toFixed(1)}%`} mono />
          )}
          {avg_phred_score != null && (
            <Field label="AVG PHRED SCORE" value={avg_phred_score.toFixed(1)} mono />
          )}
          {reads_passing_qc != null && reads_total != null && (
            <Field
              label="READS PASSING QC"
              value={`${reads_passing_qc.toLocaleString()} / ${reads_total.toLocaleString()}`}
              wide
              mono
            />
          )}
          <Field label="CREATED" value={new Date(created_at).toLocaleString()} wide />
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
  accent = false,
}: {
  label: string;
  value: string;
  mono?: boolean;
  wide?: boolean;
  accent?: boolean;
}) {
  return (
    <div className={wide ? "sm:col-span-2" : ""}>
      <dt className="font-mono text-[10px] tracking-[0.2em] uppercase text-muted font-semibold">
        {label}
      </dt>
      <dd
        className={`mt-2 break-all text-sm ${mono ? "font-mono" : ""} ${
          accent ? "text-accent" : "text-text"
        }`}
      >
        {value}
      </dd>
    </div>
  );
}
