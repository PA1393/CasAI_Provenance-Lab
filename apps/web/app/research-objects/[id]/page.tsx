import Link from "next/link";
import { getResearchObject } from "@/lib/api/client";
import { ResearchObjectSummary } from "@/components/research-objects/research-object-summary";
import { StartRunForm } from "@/components/runs/start-run-form";
import { ErrorState } from "@/components/ui/error-state";
import { Eyebrow } from "@/components/ui/eyebrow";
import { Hash } from "@/components/ui/hash";

type Props = {
  params: Promise<{ id: string }>;
};

export default async function ResearchObjectPage({ params }: Props) {
  const { id } = await params;

  let researchObject;
  try {
    researchObject = await getResearchObject(id);
  } catch {
    return (
      <div className="mx-auto max-w-3xl">
        <Link href="/research-objects" className="text-sm text-slate-500 hover:text-accent">
          ← Research Objects
        </Link>
        <div className="mt-6">
          <ErrorState message={`Could not load research object: ${id}`} />
        </div>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-3xl">
      <Link href="/research-objects" className="text-sm text-slate-500 hover:text-accent">
        ← Research Objects
      </Link>

      <div className="mt-4 flex items-start justify-between gap-6">
        <div>
          <Eyebrow>Research Object</Eyebrow>
          <h1 className="mt-1 text-2xl font-semibold text-ink">{researchObject.name}</h1>
          <Hash value={researchObject.research_object_id} length={16} className="mt-1" />
        </div>
        <StartRunForm researchObjectId={researchObject.research_object_id} />
      </div>

      <div className="mt-8">
        <ResearchObjectSummary researchObject={researchObject} />
      </div>
    </div>
  );
}
