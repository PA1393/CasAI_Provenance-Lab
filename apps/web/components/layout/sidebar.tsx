import Link from "next/link";
import { Navigation } from "./navigation";

export function Sidebar() {
  return (
    <aside className="hidden border-r border-border bg-bg-card lg:sticky lg:top-0 lg:flex lg:h-screen lg:flex-col">
      <Link href="/" aria-label="CasAI Workbench" className="px-5 pb-5 pt-7 text-center font-serif-display text-3xl text-text">CasAI</Link>
      <Navigation />
      <p className="mt-auto px-4 py-6 text-center text-xs leading-5 text-muted">Research preview</p>
    </aside>
  );
}
