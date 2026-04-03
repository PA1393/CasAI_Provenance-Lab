import Link from "next/link";
import { SiteShell } from "@/components/site-shell";

const focusAreas = [
  "Create and track computational runs before lab validation.",
  "Capture metadata, inputs, results, and provenance over time.",
  "Start with a clean, lightweight foundation that a student team can extend safely.",
];

export default function HomePage() {
  return (
    <SiteShell
      title="Research run tracking for CRISPR workflows"
      description="A clean restart of Provenance Lab with a thin frontend, a modular FastAPI backend, and a repo shape built to stay understandable."
    >
      <section className="grid gap-6 md:grid-cols-[1.3fr_0.9fr]">
        <article className="rounded-3xl border border-slate-200/80 bg-white/85 p-6 shadow-sm">
          <h2 className="text-2xl font-semibold text-ink">Current scope</h2>
          <ul className="mt-5 space-y-3 text-slate-700">
            {focusAreas.map((area) => (
              <li key={area} className="rounded-2xl bg-mist px-4 py-3 leading-7">
                {area}
              </li>
            ))}
          </ul>
        </article>

        <aside className="rounded-3xl border border-accent/20 bg-accentSoft p-6 shadow-sm">
          <p className="text-sm font-semibold uppercase tracking-[0.18em] text-accent">
            Initial outcome
          </p>
          <h2 className="mt-3 text-2xl font-semibold text-ink">Working placeholder flow</h2>
          <p className="mt-3 leading-7 text-slate-700">
            The runs page makes a real request to the backend placeholder API so the
            frontend-backend boundary is in place from day one.
          </p>
          <Link
            href="/runs"
            className="mt-6 inline-flex rounded-full bg-ink px-5 py-3 text-sm font-semibold text-white transition hover:bg-slate-800"
          >
            View runs
          </Link>
        </aside>
      </section>
    </SiteShell>
  );
}

