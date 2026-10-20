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
    <section className="mx-auto max-w-[92rem] px-4 pb-14 pt-7 sm:px-6 lg:px-8 lg:pt-9">
      <div className="flex flex-col gap-5 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-sm font-semibold text-accent">Research inputs</p>
          <h1 className="mt-1 font-serif-display text-3xl text-text sm:text-4xl">
            Your validated sequence records
          </h1>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-text-secondary sm:text-base">
            Open an existing record or add a FASTA sequence to review its source and analysis history.
          </p>
        </div>
        <Link
          href="/research-objects/new"
          className="inline-flex w-fit items-center justify-center rounded-lg bg-accent px-5 py-3 text-sm font-semibold text-bg transition-colors hover:bg-accent-bright"
        >
          Add research input
        </Link>
      </div>

      <div className="mt-7">
        {fetchError ? (
          <ErrorState message="Could not load research objects. Is the backend running?" />
        ) : items.length === 0 ? (
          <EmptyState
            message="No research inputs yet. Add a FASTA sequence to begin."
            actionLabel="Add research input"
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
