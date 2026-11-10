"use client";
import { useEffect, useState, type ReactNode } from "react";

// Execute data loading only after login. Account changes unmount this tree.
export function AsyncView({ load }: { load: () => Promise<ReactNode> }) {
  const [content, setContent] = useState<ReactNode>(null);
  const [ready, setReady] = useState(false);
  useEffect(() => {
    let active = true;
    setReady(false);
    load().then(value => { if (active) { setContent(value); setReady(true); } },
      () => { if (active) { setContent(<p role="alert" className="p-8">Could not load this workspace. Check your session and connection.</p>); setReady(true); } });
    return () => { active = false; };
  }, [load]);
  return ready ? content : <p role="status" className="p-8">Loading your workspace…</p>;
}
