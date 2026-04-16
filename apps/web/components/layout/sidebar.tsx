import Link from "next/link";

const navLinks = [
  { href: "/", label: "Overview" },
  { href: "/research-objects", label: "Research Objects" },
  { href: "/runs", label: "Runs" },
];

export function Sidebar() {
  return (
    <aside className="w-56 shrink-0 border-r border-slate-200/80 bg-white/80 px-4 py-8">
      <p className="px-3 text-xs font-semibold uppercase tracking-[0.18em] text-accent">
        CasAI
      </p>
      <nav className="mt-6 flex flex-col gap-1">
        {navLinks.map(({ href, label }) => (
          <Link
            key={href}
            href={href}
            className="rounded-xl px-3 py-2 text-sm font-medium text-slate-700 transition-colors hover:bg-mist hover:text-ink"
          >
            {label}
          </Link>
        ))}
      </nav>
    </aside>
  );
}
