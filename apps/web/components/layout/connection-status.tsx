"use client";

import { useEffect, useState } from "react";
import { getWorkspaceConnection } from "../../lib/api/client";
import { connectionCopy, type WorkspaceConnection } from "../../lib/connection-status";

export function ConnectionStatus() {
  const [connection, setConnection] = useState<WorkspaceConnection | null>(null);
  const [unavailable, setUnavailable] = useState(false);
  const [checking, setChecking] = useState(false);
  useEffect(() => {
    let active = true;
    let pending = false;
    async function check() {
      if (pending) return;
      pending = true;
      if (active) setChecking(true);
      try {
        const value = await getWorkspaceConnection();
        if (active) { setConnection(value); setUnavailable(false); }
      } catch { if (active) setUnavailable(true); }
      finally { pending = false; if (active) setChecking(false); }
    }
    void check();
    const timer = window.setInterval(() => void check(), 30_000);
    window.addEventListener("online", check);
    return () => { active = false; window.clearInterval(timer); window.removeEventListener("online", check); };
  }, []);
  const copy = connection && connectionCopy(connection);
  return <details className="border-b border-border bg-bg-card px-4 py-2 text-xs sm:px-6">
    <summary className="cursor-pointer font-semibold" aria-live="polite">
      {unavailable ? "Connection unavailable · backend could not be verified" : copy?.label ?? "Checking API connection…"}
      {checking && connection && !unavailable ? " · checking" : ""}
    </summary>
    <p className="mt-2 max-w-3xl leading-5 text-text-secondary">{unavailable
      ? "The API is unreachable or does not expose the matching demo contract. Your form is unchanged. Check the connection and backend version before submitting; inspect Runs before retrying an interrupted submission."
      : copy?.detail ?? "Checking the backend's public capabilities; no research records are sent."} Checks repeat every 30 seconds. This is not a scientific-accuracy check.</p>
  </details>;
}
