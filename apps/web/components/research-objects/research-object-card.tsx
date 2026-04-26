import Link from "next/link";
import type { ResearchObject } from "@/lib/api/client";

type Props = {
  researchObject: ResearchObject;
};

export function ResearchObjectCard({ researchObject }: Props) {
  const { research_object_id, name, pdb_id, ro_hash } = researchObject;
  return (
    <Link
      href={`/research-objects/${research_object_id}`}
      className="group block rounded-3xl border border-slate-200/80 bg-white/85 p-5 shadow-sm transition hover:border-accent/40 hover:shadow-md"
    >
      <p className="truncate font-mono text-xs text-slate-400">{research_object_id}</p>
      <p className="mt-3 truncate text-sm font-medium text-slate-700">{name}</p>
      <p className="mt-1 truncate text-xs text-slate-500">PDB: {pdb_id}</p>
      <p className="mt-4 truncate font-mono text-xs text-slate-400">hash: {ro_hash}</p>
    </Link>
  );
}
