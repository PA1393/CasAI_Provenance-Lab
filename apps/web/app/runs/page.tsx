import { SiteShell } from "@/components/site-shell";
import { fetchRuns } from "@/lib/api/client";

export default async function RunsPage() {
  const runs = await fetchRuns();

  return (
    <SiteShell
      title="Runs"
      description="Placeholder runs are served by the FastAPI backend. This keeps the frontend thin and exercises the intended API boundary early."
    >
      <section className="rounded-3xl border border-slate-200/80 bg-white/85 p-6 shadow-sm">
        <div className="flex items-center justify-between gap-4">
          <div>
            <p className="text-sm font-semibold uppercase tracking-[0.18em] text-accent">
              Backend API
            </p>
            <h2 className="mt-2 text-2xl font-semibold text-ink">Run summaries</h2>
          </div>
          <p className="rounded-full bg-mist px-4 py-2 text-sm text-slate-600">
            {runs.length} placeholder runs
          </p>
        </div>

        <div className="mt-6 overflow-hidden rounded-2xl border border-slate-200">
          <table className="min-w-full border-collapse text-left">
            <thead className="bg-slate-50 text-sm uppercase tracking-[0.16em] text-slate-500">
              <tr>
                <th className="px-4 py-3">Run</th>
                <th className="px-4 py-3">Pipeline</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Created</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200 text-sm text-slate-700">
              {runs.map((run) => (
                <tr key={run.id} className="bg-white">
                  <td className="px-4 py-4">
                    <div className="font-semibold text-ink">{run.name}</div>
                    <div className="text-xs text-slate-500">{run.id}</div>
                  </td>
                  <td className="px-4 py-4">{run.pipeline}</td>
                  <td className="px-4 py-4">
                    <span className="rounded-full bg-accentSoft px-3 py-1 text-xs font-semibold uppercase tracking-[0.14em] text-accent">
                      {run.status}
                    </span>
                  </td>
                  <td className="px-4 py-4">{new Date(run.createdAt).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </SiteShell>
  );
}

