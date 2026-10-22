import { getRuns } from "@/lib/api/client";
import { RunCard } from "@/components/runs/run-card";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";

export default async function RunsPage() {
  let runs: Awaited<ReturnType<typeof getRuns>> = [];
  let fetchError = false;

  try {
    runs = await getRuns();
  } catch {
    fetchError = true;
  }

  return (
    <section className="mx-auto max-w-[92rem] px-4 pb-14 pt-7 sm:px-6 lg:px-8 lg:pt-9">
      <p className="text-sm font-semibold text-accent">Computational runs</p>
      <h1 className="mt-1 font-serif-display text-3xl text-text sm:text-4xl">
        Track every analysis
      </h1>
      <p className="mt-2 max-w-2xl text-sm leading-6 text-text-secondary sm:text-base">
        See what is queued, running, completed, or needs attention. Open a run for its detailed stages and provenance.
      </p>

      <div className="mt-7">
        {fetchError ? (
          <ErrorState message="Could not load runs. Is the backend running?" />
        ) : runs.length === 0 ? (
          <EmptyState
            message="No runs yet. Start one from a research object."
            actionLabel="View research inputs"
            actionHref="/research-objects"
          />
        ) : (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {runs.map((run) => (
              <RunCard key={run.run_id} run={run} />
            ))}
          </div>
        )}
      </div>
    </section>
  );
}
