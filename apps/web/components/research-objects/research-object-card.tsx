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
      className="group block rounded-lg border border-border bg-bg-card p-5 hover:border-accent/60 transition-colors"
    >
      <p className="truncate font-mono text-xs text-muted">{research_object_id}</p>
      <p className="mt-3 truncate text-base font-medium text-text group-hover:text-accent transition-colors">
        {name}
      </p>
      <p className="mt-1 truncate font-mono text-xs text-muted">PDB: {pdb_id}</p>
      <p className="mt-4 truncate font-mono text-xs text-muted/70">
        hash: {ro_hash?.slice(0, 28) ?? "—"}…
      </p>
    </Link>
  );
}
