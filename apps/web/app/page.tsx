import Link from "next/link";

const sections = [
  {
    title: "Research Objects",
    description:
      "Input gene sequences and store them as structured research objects with metadata and a stable hash.",
    href: "/research-objects",
    label: "View objects",
  },
  {
    title: "Runs",
    description:
      "Start a simulation run on a research object and capture provenance, results, and status.",
    href: "/runs",
    label: "View runs",
  },
];

export default function HomePage() {
  return (
    <div className="mx-auto max-w-4xl">
      <h1 className="text-3xl font-semibold tracking-tight text-ink">
        Research run tracking for CRISPR workflows
      </h1>
      <p className="mt-3 text-base leading-7 text-slate-600">
        A clean scaffold for Provenance Lab — thin frontend, modular FastAPI backend.
      </p>

      <div className="mt-10 grid gap-5 sm:grid-cols-2">
        {sections.map(({ title, description, href, label }) => (
          <section
            key={href}
            className="rounded-3xl border border-slate-200/80 bg-white/85 p-6 shadow-sm"
          >
            <h2 className="text-xl font-semibold text-ink">{title}</h2>
            <p className="mt-3 leading-7 text-slate-600">{description}</p>
            <Link
              href={href}
              className="mt-5 inline-flex rounded-full bg-ink px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-slate-800"
            >
              {label}
            </Link>
          </section>
        ))}
      </div>
    </div>
  );
}
