"use client";
import { useEffect, useState, type ReactNode } from "react";
import { getWorkspaceMode } from "../../lib/api/client";
import { setSession } from "../../lib/auth-session";
import { AuthGate } from "./auth-gate";

// Login remains implemented but is mounted only when the backend enables accounts.
export function WorkspaceGate({ children }: { children: ReactNode }) {
  const [mode, setMode] = useState<"demo" | "accounts" | null>(null);
  const [error, setError] = useState(false);
  const [retry, setRetry] = useState(0);
  useEffect(() => {
    let active = true;
    getWorkspaceMode().then(value => {
      if (!active) return;
      if (value === "demo") setSession(null);
      setMode(value);
    }, () => { if (active) setError(true); });
    return () => { active = false; };
  }, [retry]);
  if (error) return <main id="main-content" className="mx-auto max-w-lg p-10">
    <h1 className="font-serif-display text-3xl">Demo backend needs attention</h1>
    <p className="mt-4 text-sm leading-6">Connection unavailable or backend version mismatch. The workspace could not be verified. Check the API connection and deploy the matching backend before uploading data. No database persistence has been verified.</p>
    <button onClick={() => { setError(false); setRetry(value => value + 1); }} className="mt-5 rounded-lg bg-accent px-4 py-3 text-bg">Check connection again</button>
  </main>;
  if (!mode) return <main id="main-content" className="p-10" role="status">Opening workspace…</main>;
  if (mode === "accounts") return <AuthGate>{children}</AuthGate>;
  return <div><p className="border-b border-border bg-accent-soft px-6 py-3 text-xs leading-5">
    No-login demo · shared demo workspace, not a private account. Use public or synthetic data only. Login is saved for a later release.
  </p>{children}</div>;
}
