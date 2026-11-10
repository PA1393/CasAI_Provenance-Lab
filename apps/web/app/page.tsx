"use client";
import Link from "next/link";
import { AsyncView } from "../components/layout/async-view";
import { getRunMetrics, type RunMetrics } from "../lib/api/client";

async function loadWorkbench() {
  let stats: RunMetrics | null = null;
  try { stats = await getRunMetrics(); } catch { /* Show unavailable, never zero. */ }
  return <section className="mx-auto max-w-5xl px-6 py-10">
    <h1 className="font-serif-display text-4xl">Your workbench</h1>
    <p className="mt-3 text-text-secondary">Start research or organize inputs and runs in this workspace. Historical sample records are not automatically imported.</p>
    <div className="mt-8 grid gap-5 sm:grid-cols-2">
      <Link href="/research-objects/new" className="rounded-2xl border border-border bg-bg-card p-7"><h2 className="text-xl font-semibold text-accent">Add research →</h2><p className="mt-3 text-sm text-text-secondary">Upload a sequence, review it and choose an analysis.</p></Link>
      <Link href="/folders" className="rounded-2xl border border-border bg-bg-card p-7"><h2 className="text-xl font-semibold text-accent">Your folders →</h2><p className="mt-3 text-sm text-text-secondary">Group inputs and runs by project.</p></Link>
    </div>
    <section className="mt-6 rounded-2xl border border-border bg-bg-card p-7">
      <h2 className="text-lg font-semibold">Run completion rate</h2>
      <p className="mt-3 font-serif-display text-4xl">{stats?.percent == null ? "—" : `${stats.percent}%`}</p>
      <p className="mt-3 text-sm text-text-secondary">{stats ? `${stats.completed} completed / ${stats.finished} finished runs · ${stats.pending} queued or running (excluded)` : "Statistics unavailable. Check your connection."}</p>
      <p className="mt-2 text-xs leading-6 text-muted">Workflow completion only—not editing efficiency, biological success, or predictive accuracy. No percentage is shown until a run finishes.</p>
    </section>
  </section>;
}
export default function Page() { return <AsyncView load={loadWorkbench} />; }
