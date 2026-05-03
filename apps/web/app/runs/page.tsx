import { getRuns } from "@/lib/api/client";
import { RunCard } from "@/components/runs/run-card";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { Eyebrow } from "@/components/ui/eyebrow";

export default async function RunsPage() {
  let runs: Awaited<ReturnType<typeof getRuns>> = [];
  let fetchError = false;

  try {
    runs = await getRuns();
  } catch {
    fetchError = true;
  }

  return (
    <section className="px-8 pt-12 pb-12 max-w-7xl mx-auto">
      <Eyebrow>──── LAYER 3 + LAYER 4 / RUNS</Eyebrow>
      <h1 className="mt-4 font-serif-display text-4xl md:text-5xl">
        Pipeline <span className="italic text-accent">Runs.</span>
      </h1>
      <p className="mt-3 text-muted max-w-2xl">
        Each run executes a research object through the five-stage pipeline. Every step is
        recorded with timestamps and hashes.
      </p>

      <div className="mt-10">
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
    </section>
  );
}
