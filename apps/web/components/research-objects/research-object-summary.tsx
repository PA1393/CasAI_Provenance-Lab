import type { ResearchObject } from "@/lib/api/client";

type Props = {
  researchObject: ResearchObject;
};

export function ResearchObjectSummary({ researchObject }: Props) {
  const { research_object_id, sequence_data, metadata, structure_reference, hash } = researchObject;
  return (
    <div className="rounded-3xl border border-slate-200/80 bg-white/85 p-6 shadow-sm">
      <dl className="grid gap-5 sm:grid-cols-2">
        <Field label="ID" value={research_object_id} mono />
        <Field label="Hash" value={hash} mono />
        <Field label="Sequence Data" value={sequence_data} wide />
        {structure_reference && (
          <Field label="Structure Reference" value={structure_reference} />
        )}
      </dl>

      {Object.keys(metadata).length > 0 && (
        <div className="mt-6">
          <p className="mb-3 text-sm font-semibold text-slate-500">Metadata</p>
          <dl className="grid gap-3 sm:grid-cols-2">
            {Object.entries(metadata).map(([key, value]) => (
              <Field key={key} label={key} value={value} />
            ))}
          </dl>
        </div>
      )}
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
