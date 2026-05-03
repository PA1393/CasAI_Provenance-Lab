import Link from "next/link";
import { Eyebrow } from "@/components/ui/eyebrow";

export default function HomePage() {
  return (
    <div className="min-h-[calc(100vh-80px)]">
      {/* Hero */}
      <section className="px-8 pt-16 pb-12 max-w-7xl mx-auto">
        <Eyebrow>──── PROVENANCE LAB / V0.2</Eyebrow>
        <h1 className="font-serif-display text-5xl md:text-6xl mt-6 max-w-4xl leading-tight">
          Provenance-first <span className="italic text-accent">gene simulation,</span>
          <br />
          hashed and explained.
        </h1>
        <p className="mt-6 text-lg text-muted max-w-2xl italic">
          The system of record for gene editing. Upload your inputs, run a simulation,
          get a reproducible result.
        </p>
        <div className="mt-8 flex flex-wrap gap-3">
          <Link
            href="/research-objects/new"
            className="font-mono text-xs tracking-[0.2em] uppercase font-semibold px-5 py-3 rounded bg-text text-bg hover:bg-accent transition-colors"
          >
            + New Research Object
          </Link>
          <Link
            href="/research-objects"
            className="font-mono text-xs tracking-[0.2em] uppercase font-semibold px-5 py-3 rounded border border-border text-text hover:border-accent hover:text-accent transition-colors"
          >
            View Research Objects →
          </Link>
          <Link
            href="/runs"
            className="font-mono text-xs tracking-[0.2em] uppercase font-semibold px-5 py-3 rounded border border-border text-text hover:border-accent hover:text-accent transition-colors"
          >
            View Runs →
          </Link>
        </div>
      </section>

      {/* Two-up section cards */}
      <section className="px-8 max-w-7xl mx-auto pb-16">
        <Eyebrow>──── WHAT YOU CAN DO</Eyebrow>
        <div className="mt-6 grid gap-5 sm:grid-cols-2">
          <SectionCard
            title="Research Objects"
            description="Input gene sequences and store them as structured research objects with metadata and a stable content-addressable hash."
            href="/research-objects"
            label="View objects"
          />
          <SectionCard
            title="Runs"
            description="Start a simulation run on a research object and capture provenance, results, and status across the five-stage pipeline."
            href="/runs"
            label="View runs"
          />
        </div>
      </section>
    </div>
  );
}

function SectionCard({
  title,
  description,
  href,
  label,
}: {
  title: string;
  description: string;
  href: string;
  label: string;
}) {
  return (
    <section className="rounded-lg border border-border bg-bg-card p-6">
      <h2 className="font-serif-display italic text-2xl text-text">{title}</h2>
      <p className="mt-3 leading-7 text-muted">{description}</p>
      <Link
        href={href}
        className="mt-5 inline-flex font-mono text-xs tracking-[0.2em] uppercase font-semibold px-4 py-2 rounded border border-border text-text hover:border-accent hover:text-accent transition-colors"
      >
        {label} →
      </Link>
    </section>
  );
}
