import Link from "next/link";
import { getResearchObject, getRunsByResearchObject } from "@/lib/api/client";
import { ResearchObjectSummary } from "@/components/research-objects/research-object-summary";
import { RunCard } from "@/components/runs/run-card";
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
  let runs;
  try {
    [researchObject, runs] = await Promise.all([
      getResearchObject(id),
      getRunsByResearchObject(id),
    ]);
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

      <div className="mt-12 ">
        <Eyebrow>──── RUNS</Eyebrow>
        {runs.length === 0 ? (
          <p className="mt-4 text-sm text-muted">No runs yet.</p>
        ) : (
          <div className="mt-4 grid gap-3">
            {runs.map((run) => (
              <RunCard key={run.run_id} run={run} />
            ))}
          </div>
        )}
      </div>
    </section>
  );
}
