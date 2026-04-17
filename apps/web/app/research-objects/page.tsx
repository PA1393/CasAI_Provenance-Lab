import Link from "next/link";
import { getResearchObjects } from "@/lib/api/client";
import { ResearchObjectCard } from "@/components/research-objects/research-object-card";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";

export default async function ResearchObjectsPage() {
  let items: Awaited<ReturnType<typeof getResearchObjects>> = [];
  let fetchError = false;

  try {
    items = await getResearchObjects();
  } catch {
    fetchError = true;
  }

  return (
    <div className="mx-auto max-w-4xl">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold text-ink">Research Objects</h1>
        <Link
          href="/research-objects/new"
          className="inline-flex rounded-full bg-ink px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-slate-800"
        >
          New
        </Link>
      </div>

      <div className="mt-8">
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
    </div>
  );
}
