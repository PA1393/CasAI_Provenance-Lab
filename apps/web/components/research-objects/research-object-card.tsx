import Link from "next/link";
import type { ResearchObject } from "@/lib/api/client";

type Props = {
  researchObject: ResearchObject;
};

export function ResearchObjectCard({ researchObject }: Props) {
  const { research_object_id, sequence_data, hash } = researchObject;
  return (
    <Link
      href={`/research-objects/${research_object_id}`}
      className="group block rounded-3xl border border-slate-200/80 bg-white/85 p-5 shadow-sm transition hover:border-accent/40 hover:shadow-md"
    >
      <p className="truncate font-mono text-xs text-slate-400">{research_object_id}</p>
      <p className="mt-3 truncate text-sm text-slate-700">
        {sequence_data.length > 60 ? `${sequence_data.slice(0, 60)}…` : sequence_data}
      </p>
      <p className="mt-4 truncate font-mono text-xs text-slate-400">hash: {hash}</p>
    </Link>
  );
}
