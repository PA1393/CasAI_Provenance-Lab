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
    <div className="mx-auto max-w-4xl">
      <h1 className="text-2xl font-semibold text-ink">Runs</h1>

      <div className="mt-8">
        {fetchError ? (
          <ErrorState message="Could not load runs. Is the backend running?" />
        ) : runs.length === 0 ? (
          <EmptyState
            message="No runs yet. Start one from a research object."
            actionLabel="View Research Objects"
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
    </div>
  );
}
