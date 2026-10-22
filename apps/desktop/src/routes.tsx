import type { ReactNode } from "react";

// These existing view functions only fetch public API data and return React
// elements. Vite compiles them as browser modules; no Next server is bundled.
export async function loadRoute(path: string): Promise<ReactNode> {
  if (path === "/") return (await import("../../web/app/page")).default();
  if (path === "/research-objects") return (await import("../../web/app/research-objects/page")).default();
  if (path === "/research-objects/new") return (await import("../../web/app/research-objects/new/page")).default();
  if (path === "/runs") return (await import("../../web/app/runs/page")).default();
  const match = /^\/(research-objects|runs)\/([A-Za-z0-9_-]{1,128})$/.exec(path);
  if (match) {
    const params = Promise.resolve({ id: match[2] });
    return match[1] === "runs"
      ? (await import("../../web/app/runs/[id]/page")).default({ params })
      : (await import("../../web/app/research-objects/[id]/page")).default({ params });
  }
  return <section className="p-8"><h1 className="font-serif-display text-3xl">Page not found</h1><a href="#/" className="text-accent">Return to Workbench</a></section>;
}
