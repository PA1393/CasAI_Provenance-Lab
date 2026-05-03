import Link from "next/link";

export function Header() {
  return (
    <nav className="flex items-center justify-between px-8 py-5 border-b border-border/50">
      <Link href="/" className="flex items-center gap-3 group">
        <div className="relative w-5 h-5">
          <div className="absolute inset-0 rounded-full border border-accent" />
          <div className="absolute inset-[5px] rounded-full bg-accent" />
        </div>
        <span className="font-mono text-sm tracking-[0.3em] text-text font-semibold group-hover:text-accent transition-colors">
          CASAI
        </span>
      </Link>

      <div className="hidden md:flex items-center gap-8">
        <Link
          href="/"
          className="font-mono text-xs tracking-[0.2em] text-muted hover:text-text transition-colors"
        >
          DASHBOARD
        </Link>
        <Link
          href="/research-objects"
          className="font-mono text-xs tracking-[0.2em] text-muted hover:text-text transition-colors"
        >
          RESEARCH OBJECTS
        </Link>
        <Link
          href="/runs"
          className="font-mono text-xs tracking-[0.2em] text-muted hover:text-text transition-colors"
        >
          RUNS
        </Link>
        <Link
          href="/research-objects/new"
          className="font-mono text-xs tracking-[0.2em] text-muted hover:text-text transition-colors"
        >
          NEW RESEARCH OBJECT
        </Link>
      </div>

      <div className="flex items-center gap-2 px-3 py-1 rounded-full border border-accent/60">
        <div className="w-1.5 h-1.5 rounded-full bg-accent animate-pulse-soft" />
        <span className="font-mono text-[10px] tracking-[0.2em] text-accent font-semibold">
          PHASE 1 · DEMO SPRINT
        </span>
      </div>
    </nav>
  );
}
