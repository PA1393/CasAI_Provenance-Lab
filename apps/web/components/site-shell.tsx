import Link from "next/link";
import type { ReactNode } from "react";

type SiteShellProps = {
  children: ReactNode;
  title: string;
  description: string;
};

export function SiteShell({ children, title, description }: SiteShellProps) {
  return (
    <main className="mx-auto flex min-h-screen w-full max-w-5xl flex-col px-6 py-10 md:px-10">
      <header className="mb-10 rounded-3xl border border-slate-200/80 bg-white/80 p-6 shadow-sm backdrop-blur">
        <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
          <div className="max-w-2xl">
            <p className="text-sm font-semibold uppercase tracking-[0.2em] text-accent">
              CasAI Provenance Lab
            </p>
            <h1 className="mt-3 text-4xl font-semibold tracking-tight text-ink">
              {title}
            </h1>
            <p className="mt-3 text-base leading-7 text-slate-600">{description}</p>
          </div>
          <nav className="flex gap-3 text-sm font-medium text-slate-700">
            <Link className="rounded-full border border-slate-200 px-4 py-2 hover:border-accent hover:text-accent" href="/">
              Overview
            </Link>
            <Link className="rounded-full border border-slate-200 px-4 py-2 hover:border-accent hover:text-accent" href="/runs">
              Runs
            </Link>
          </nav>
        </div>
      </header>
      {children}
    </main>
  );
}

