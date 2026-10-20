"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const items = [
  { href: "/", label: "Workbench", path: "M3 10 12 3l9 7M5 9v12h5v-7h4v7h5V9" },
  { href: "/research-objects", label: "Inputs", path: "M6 3h8l4 4v14H6ZM14 3v5h4" },
  { href: "/runs", label: "Runs", path: "m7 3 14 9-14 9Z" },
] as const;

export function Navigation({ mobile = false }: { mobile?: boolean }) {
  const pathname = usePathname();
  return (
    <nav aria-label={mobile ? "Mobile navigation" : "Primary navigation"} className={mobile ? "flex gap-1 px-3 pb-3 lg:hidden" : "space-y-3 px-3 py-5"}>
      {items.map((item) => {
        const active = item.href === "/" ? pathname === "/" : pathname === item.href || pathname.startsWith(`${item.href}/`);
        return (
          <Link key={item.href} href={item.href} aria-current={active ? "page" : undefined} className={`flex items-center justify-center rounded-lg text-sm font-medium transition-colors ${mobile ? "flex-1 gap-2 px-3 py-2" : "flex-col gap-2 px-2 py-4"} ${active ? "bg-accent-soft text-accent" : "text-text-secondary hover:bg-bg-sunken hover:text-text"}`}>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" className={mobile ? "h-4 w-4" : "h-6 w-6"} aria-hidden="true"><path d={item.path} /></svg>
            {item.label}
          </Link>
        );
      })}
    </nav>
  );
}
