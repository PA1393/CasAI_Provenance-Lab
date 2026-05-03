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
      <section className="px-8 pt-12 pb-12 max-w-4xl mx-auto">
        <Link href="/research-objects" className="font-mono text-xs tracking-[0.2em] uppercase text-muted hover:text-accent transition-colors">
          ← RESEARCH OBJECTS
        </Link>
        <div className="mt-6">
          <ErrorState message={`Could not load research object: ${id}`} />
        </div>
      </section>
    );
  }

  return (
    <section className="px-8 pt-12 pb-12 max-w-4xl mx-auto">
      <Link href="/research-objects" className="font-mono text-xs tracking-[0.2em] uppercase text-muted hover:text-accent transition-colors">
        ← RESEARCH OBJECTS
      </Link>

      <div className="mt-6 flex items-start justify-between gap-6">
        <div>
          <Eyebrow>──── RESEARCH OBJECT</Eyebrow>
          <h1 className="mt-3 font-serif-display text-3xl md:text-4xl">
            {researchObject.name}
          </h1>
          <Hash value={researchObject.research_object_id} length={16} className="mt-2 block" />
        </div>
        <StartRunForm researchObjectId={researchObject.research_object_id} />
      </div>

      <div className="mt-10">
        <ResearchObjectSummary researchObject={researchObject} />
      </div>
    </section>
  );
}
