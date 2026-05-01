import Link from "next/link";

export function Header() {
  return (
    <header className="flex items-center justify-between border-b border-slate-200/80 bg-white/80 px-8 py-4 backdrop-blur">
      <Link href="/" className="group flex items-center gap-3">
        <div className="relative h-5 w-5">
          <div className="absolute inset-0 rounded-full border border-accent" />
          <div className="absolute inset-[5px] rounded-full bg-accent" />
        </div>
        <span className="font-mono text-sm font-semibold tracking-[0.3em] text-slate-800 transition-colors group-hover:text-accent">
          CASAI
        </span>
      </Link>

      <nav className="hidden items-center gap-8 md:flex">
        <Link
          href="/runs"
          className="font-mono text-xs tracking-[0.2em] text-slate-400 transition-colors hover:text-slate-800"
        >
          RUNS
        </Link>
        <Link
          href="/research-objects"
          className="font-mono text-xs tracking-[0.2em] text-slate-400 transition-colors hover:text-slate-800"
        >
          RESEARCH OBJECTS
        </Link>
        <Link
          href="/research-objects/new"
          className="font-mono text-xs tracking-[0.2em] text-slate-400 transition-colors hover:text-slate-800"
        >
          NEW
        </Link>
      </nav>

      <div className="flex items-center gap-2 rounded-full border border-accent/60 px-3 py-1">
        <div className="h-1.5 w-1.5 animate-pulse rounded-full bg-accent" />
        <span className="font-mono text-[10px] font-semibold tracking-[0.2em] text-accent">
          MVP · DEMO
        </span>
      </div>
    </header>
  );
}
