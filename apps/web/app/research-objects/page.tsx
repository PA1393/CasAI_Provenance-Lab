import Link from "next/link";
import { getResearchObjects } from "@/lib/api/client";
import { ResearchObjectCard } from "@/components/research-objects/research-object-card";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { Eyebrow } from "@/components/ui/eyebrow";

export default async function ResearchObjectsPage() {
  let items: Awaited<ReturnType<typeof getResearchObjects>> = [];
  let fetchError = false;

  try {
    items = await getResearchObjects();
  } catch {
    fetchError = true;
  }

  return (
    <section className="px-8 pt-12 pb-12 max-w-7xl mx-auto">
      <Eyebrow>──── LAYER 2 / RESEARCH OBJECTS</Eyebrow>
      <div className="mt-4 flex items-end justify-between">
        <div>
          <h1 className="font-serif-display text-4xl md:text-5xl">
            Research <span className="italic text-accent">Objects</span>
          </h1>
          <p className="mt-3 text-muted max-w-2xl">
            Canonical, immutable bundles. Each one represents a validated gene-editing input,
            hashed and ready for runs.
          </p>
        </div>
        <Link
          href="/research-objects/new"
          className="font-mono text-xs tracking-[0.2em] uppercase font-semibold px-5 py-3 rounded bg-text text-bg hover:bg-accent transition-colors"
        >
          + New Research Object
        </Link>
      </div>

      <div className="mt-10">
        {fetchError ? (
          <ErrorState message="Could not load research objects. Is the backend running?" />
        ) : items.length === 0 ? (
          <EmptyState
            message="No research objects yet."
            actionLabel="Create one"
            actionHref="/research-objects/new"
          />
        ) : (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {items.map((ro) => (
              <ResearchObjectCard key={ro.research_object_id} researchObject={ro} />
            ))}
          </div>
        )}
      </div>
    </section>
  );
}
