import Link from "next/link";
import { Navigation } from "./navigation";
import { ThemeToggle } from "./theme-toggle";
import { DemoFeedback } from "./demo-feedback";

export function Header() {
  return (
    <header className="border-b border-border bg-bg/95 lg:border-0 lg:bg-transparent">
      <div className="mx-auto flex max-w-[92rem] flex-wrap items-center justify-between gap-3 px-4 pb-3 pt-4 sm:px-6 lg:justify-end lg:px-8 lg:pt-6">
        <Link href="/" className="font-serif-display text-2xl lg:hidden">CasAI</Link>
        <div className="flex items-center gap-3"><DemoFeedback /><ThemeToggle /></div>
      </div>
      <Navigation mobile />
    </header>
  );
}
