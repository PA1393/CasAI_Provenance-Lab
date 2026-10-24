import Link from "next/link";

import {
  getHealth,
  getResearchObjects,
  getRuns,
  type ResearchObject,
  type Run,
} from "@/lib/api/client";
import { RunStatusBadge } from "@/components/runs/run-status-badge";

export default async function HomePage() {
  const [healthResult, objectsResult, runsResult] = await Promise.allSettled([
    getHealth(),
    getResearchObjects(),
    getRuns(),
  ]);

  const connected = healthResult.status === "fulfilled";
  const objects = sortNewest(
    objectsResult.status === "fulfilled" ? objectsResult.value : [],
  );
  const runs = sortNewest(runsResult.status === "fulfilled" ? runsResult.value : []);
  const dataUnavailable =
    objectsResult.status === "rejected" || runsResult.status === "rejected";
  const activeRuns = runs.filter((run) => run.status === "running" || run.status === "queued");
  const completedRuns = runs.filter((run) => run.status === "completed");
  const continueRun = activeRuns[0] ?? runs[0] ?? null;
  const continueObject = objects[0] ?? null;

  return (
    <section className="mx-auto max-w-[92rem] px-4 pb-14 pt-7 sm:px-6 lg:px-8 lg:pt-9">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="mt-1 font-serif-display text-3xl text-text sm:text-4xl">
            Workbench
          </h1>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-text-secondary sm:text-base">
            Your inputs, runs, and results.
          </p>
        </div>
        <div
          className={`inline-flex w-fit items-center gap-2 rounded-full border px-3 py-1.5 text-xs font-medium ${
            connected
              ? "border-accent/25 bg-accent-soft text-accent"
              : "border-accent-amber/30 bg-accent-amber/10 text-accent-amber"
          }`}
        >
          <span className={`h-2 w-2 rounded-full ${connected ? "bg-accent" : "bg-accent-amber"}`} />
          {connected ? "API reachable" : "Backend unavailable"}
        </div>
      </div>

      {dataUnavailable && (
        <div className="mt-6 rounded-xl border border-accent-amber/30 bg-accent-amber/10 px-4 py-3 text-sm text-accent-amber">
          Existing work could not be loaded. You can still open intake, or restart the API and refresh.
        </div>
      )}

      <div className="mt-7 grid gap-5 xl:grid-cols-[minmax(0,1.45fr)_minmax(22rem,0.75fr)]">
        <StartResearchCard />
        <ContinueCard run={continueRun} researchObject={continueObject} unavailable={dataUnavailable} />
      </div>

      <dl className="mt-5 grid gap-3 sm:grid-cols-3">
        <Metric label="Research inputs" value={objectsResult.status === "fulfilled" ? objects.length : null} detail="source records" />
        <Metric label="Active runs" value={runsResult.status === "fulfilled" ? activeRuns.length : null} detail="queued or processing" />
        <Metric label="Completed runs" value={runsResult.status === "fulfilled" ? completedRuns.length : null} detail="ready to inspect" />
      </dl>

      <div className="mt-5 grid gap-5 xl:grid-cols-2">
        <RecentInputs items={objects.slice(0, 5)} unavailable={objectsResult.status === "rejected"} />
        <RecentRuns items={runs.slice(0, 5)} unavailable={runsResult.status === "rejected"} />
      </div>
    </section>
  );
}

function StartResearchCard() {
  return (
    <section className="overflow-hidden rounded-2xl border border-border-strong bg-bg-card shadow-raised">
      <div className="min-h-[17rem]">
        <div className="flex flex-col p-6 sm:p-8">
          <div className="flex items-center gap-3">
            <span className="grid h-11 w-11 place-items-center rounded-xl bg-accent-soft text-accent">
              <svg viewBox="0 0 24 24" fill="none" aria-hidden="true" className="h-6 w-6">
                <path d="M7 3.75h6l4 4v12.5H7z" stroke="currentColor" strokeWidth="1.7" />
                <path d="M13 3.75v4h4M9.5 12h5M9.5 15.5h5" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" />
              </svg>
            </span>
            <div>
              <h2 className="font-serif-display text-2xl text-text">New analysis</h2>
            </div>
          </div>
          <div className="mt-6 grid gap-4 sm:grid-cols-3" aria-label="Intake process">
            <Step number="1" label="Choose FASTA" detail="Select your sequence file." />
            <Step number="2" label="Review input" detail="Check the detected details." />
            <Step number="3" label="Confirm record" detail="Save, then start a run." />
          </div>
          <div className="mt-auto flex flex-col gap-3 pt-7 sm:flex-row">
            <Link
              href="/research-objects/new"
              className="inline-flex items-center justify-center rounded-lg bg-accent px-5 py-3 text-sm font-semibold text-bg transition-colors hover:bg-accent-bright"
            >
              Add FASTA input <span aria-hidden="true" className="ml-2">→</span>
            </Link>
            <Link
              href="/research-objects"
              className="inline-flex items-center justify-center rounded-lg border border-border-strong px-5 py-3 text-sm font-semibold text-text transition-colors hover:bg-bg-sunken"
            >
              Browse existing inputs
            </Link>
          </div>
        </div>
      </div>
    </section>
  );
}

function ContinueCard({
  run,
  researchObject,
  unavailable,
}: {
  run: Run | null;
  researchObject: ResearchObject | null;
  unavailable: boolean;
}) {
  if (run) {
    return (
      <section className="flex min-h-[19rem] flex-col rounded-2xl border border-border-strong bg-bg-card p-6 shadow-card sm:p-7">
        <div className="flex items-center justify-between gap-3">
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-muted">Continue work</p>
          <RunStatusBadge status={run.status} overview />
        </div>
        <h2 className="mt-6 line-clamp-2 text-2xl font-semibold leading-tight text-text">{run.prompt}</h2>
        <p className="mt-2 font-mono text-xs text-muted">{shortId(run.run_id)}</p>
        <div className="mt-6 rounded-xl bg-bg-sunken p-4">
          <p className="text-xs text-muted">Current stage</p>
          <p className="mt-1 font-semibold text-text">{humanizeStage(run.current_stage)}</p>
        </div>
        <Link
          href={`/runs/${run.run_id}`}
          className="mt-auto inline-flex items-center justify-between rounded-lg border border-border-strong px-4 py-3 text-sm font-semibold text-text transition-colors hover:border-accent hover:text-accent"
        >
          Open run <span aria-hidden="true">→</span>
        </Link>
      </section>
    );
  }

  if (researchObject) {
    return (
      <section className="flex min-h-[19rem] flex-col rounded-2xl border border-border-strong bg-bg-card p-6 shadow-card sm:p-7">
        <p className="text-xs font-semibold uppercase tracking-[0.16em] text-muted">Latest input</p>
        <h2 className="mt-6 text-2xl font-semibold text-text">{researchObject.name}</h2>
        <p className="mt-2 text-sm text-text-secondary">
          {researchObject.sequence_length?.toLocaleString() ?? "Unknown"} bp · {researchObject.input_file_type.toUpperCase()}
        </p>
        <p className="mt-5 break-all font-mono text-xs leading-5 text-muted">{shortId(researchObject.ro_hash)}</p>
        <Link
          href={`/research-objects/${researchObject.research_object_id}`}
          className="mt-auto inline-flex items-center justify-between rounded-lg border border-border-strong px-4 py-3 text-sm font-semibold text-text transition-colors hover:border-accent hover:text-accent"
        >
          Open input <span aria-hidden="true">→</span>
        </Link>
      </section>
    );
  }

  return (
    <section className="flex min-h-[19rem] flex-col justify-center rounded-2xl border border-dashed border-border-strong bg-bg-card p-7 text-center">
      <p className="text-lg font-semibold text-text">{unavailable ? "Existing work unavailable" : "Nothing to continue yet"}</p>
      <p className="mx-auto mt-2 max-w-sm text-sm leading-6 text-text-secondary">
        {unavailable ? "Reconnect the backend and refresh to resume your work." : "Your most recent input or run will appear here after you begin."}
      </p>
    </section>
  );
}

function Metric({ label, value, detail }: { label: string; value: number | null; detail: string }) {
  return (
    <div className="rounded-xl border border-border bg-bg-card px-5 py-4 shadow-card">
      <dt className="text-xs font-medium text-muted">{label}</dt>
      <dd className="mt-2 flex items-baseline gap-2">
        <span className="font-serif-display text-3xl text-text">{value ?? "—"}</span>
        <span className="text-xs text-muted">{detail}</span>
      </dd>
    </div>
  );
}

function RecentInputs({ items, unavailable }: { items: ResearchObject[]; unavailable: boolean }) {
  return (
    <section className="rounded-2xl border border-border bg-bg-card shadow-card">
      <SectionHeading title="Recent inputs" href="/research-objects" />
      {items.length === 0 ? (
        <EmptyList copy={unavailable ? "Research inputs could not be loaded." : "No research inputs yet."} />
      ) : (
        <ul className="divide-y divide-border">
          {items.map((item) => (
            <li key={item.research_object_id}>
              <Link href={`/research-objects/${item.research_object_id}`} className="flex items-center gap-4 px-5 py-4 hover:bg-bg-sunken/60">
                <span className="grid h-9 w-9 shrink-0 place-items-center rounded-lg bg-accent-soft text-xs font-bold text-accent">DNA</span>
                <span className="min-w-0 flex-1">
                  <span className="block truncate text-sm font-semibold text-text">{item.name}</span>
                  <span className="mt-1 block truncate text-xs text-muted">
                    {item.input_file_type.toUpperCase()} · {item.sequence_length?.toLocaleString() ?? "—"} bp
                  </span>
                </span>
                <span className="hidden text-xs text-muted sm:block">{formatDate(item.created_at)}</span>
                <span aria-hidden="true" className="text-muted">→</span>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

function RecentRuns({ items, unavailable }: { items: Run[]; unavailable: boolean }) {
  return (
    <section className="rounded-2xl border border-border bg-bg-card shadow-card">
      <SectionHeading title="Recent runs" href="/runs" />
      {items.length === 0 ? (
        <EmptyList copy={unavailable ? "Runs could not be loaded." : "No computational runs yet."} />
      ) : (
        <ul className="divide-y divide-border">
          {items.map((item) => (
            <li key={item.run_id}>
              <Link href={`/runs/${item.run_id}`} className="flex items-center gap-4 px-5 py-4 hover:bg-bg-sunken/60">
                <span className="min-w-0 flex-1">
                  <span className="block truncate text-sm font-semibold text-text">{item.prompt}</span>
                  <span className="mt-1 block truncate text-xs text-muted">
                    {humanizeStage(item.current_stage)} · {formatDate(item.created_at)}
                  </span>
                </span>
                <RunStatusBadge status={item.status} overview />
                <span aria-hidden="true" className="text-muted">→</span>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

function SectionHeading({ title, href }: { title: string; href: string }) {
  return (
    <div className="flex items-center justify-between border-b border-border px-5 py-4">
      <h2 className="text-base font-semibold text-text">{title}</h2>
      <Link href={href} className="text-xs font-semibold text-accent hover:text-accent-bright">View all</Link>
    </div>
  );
}

function EmptyList({ copy }: { copy: string }) {
  return <p className="px-5 py-10 text-center text-sm text-muted">{copy}</p>;
}

function Step({ number, label, detail }: { number: string; label: string; detail: string }) {
  return (
    <div>
      <span className="mb-3 grid h-8 w-8 place-items-center rounded-full bg-accent-soft text-sm font-semibold text-accent">{number}</span>
      <p className="text-sm font-semibold text-text">{label}</p>
      <p className="mt-1 text-xs leading-5 text-text-secondary">{detail}</p>
    </div>
  );
}

function sortNewest<T extends { created_at: string }>(items: T[]): T[] {
  return [...items].sort(
    (left, right) => new Date(right.created_at).getTime() - new Date(left.created_at).getTime(),
  );
}

function shortId(value: string): string {
  if (value.length <= 30) return value;
  return `${value.slice(0, 18)}…${value.slice(-8)}`;
}

function humanizeStage(stage: string | null): string {
  if (!stage) return "Not started";
  const labels: Record<string, string> = {
    input: "Checking source input",
    fields: "Extracting fields",
    extract: "Preparing sequence data",
    simulate: "Running computation",
    score: "Scoring results",
    results: "Recording results",
    summary: "Preparing summary",
  };
  return labels[stage] ?? stage.replaceAll("_", " ");
}

function formatDate(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Unknown date";
  return new Intl.DateTimeFormat("en", { month: "short", day: "numeric" }).format(date);
}
