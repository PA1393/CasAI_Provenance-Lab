import { useEffect, useState, type ReactNode } from "react";
import { SiteShell } from "../../web/components/layout/site-shell";
import { usePathname, useRefreshRevision, useRouter } from "./compat/navigation";
import { checkConnection, getPublicEnv, saveApiUrl } from "./connection";
import { loadRoute } from "./routes";

type ConnectionState = "checking" | "connected" | "outdated" | "unavailable";

export function DesktopApp() {
  const path = usePathname();
  const revision = useRefreshRevision();
  const router = useRouter();
  const [endpoint, setEndpoint] = useState(getPublicEnv().NEXT_PUBLIC_API_BASE_URL);
  const [draft, setDraft] = useState(endpoint);
  const [connection, setConnection] = useState<ConnectionState>("checking");
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [probe, setProbe] = useState(0);
  const [message, setMessage] = useState<string | null>(null);
  const [content, setContent] = useState<ReactNode>(null);
  const [loadedKey, setLoadedKey] = useState("");
  const key = `${endpoint}:${path}:${revision}`;

  useEffect(() => {
    let active = true;
    setConnection("checking");
    checkConnection(endpoint).then(
      (status) => { if (active) setConnection(status === "ready" ? "connected" : "outdated"); },
      () => { if (active) setConnection("unavailable"); },
    );
    return () => { active = false; };
  }, [endpoint, probe]);

  useEffect(() => {
    let active = true;
    loadRoute(path).then((page) => {
      if (active) { setContent(page); setLoadedKey(key); }
    }).catch(() => {
      if (active) {
        setContent(<div role="alert" className="p-8">Could not load this screen. Check your connection, then retry.</div>);
        setLoadedKey(key);
      }
    });
    return () => { active = false; };
  }, [key, path]);

  return <SiteShell>
    <div className="mx-auto flex max-w-[92rem] flex-wrap items-center justify-between gap-3 border-b border-border px-6 py-3 text-xs">
      <p role="status" className={connection === "unavailable" || connection === "outdated" ? "text-accent-amber" : "text-text-secondary"}>
        Desktop demo · {connection === "checking" ? "Checking backend…" : connection === "connected" ? "Required backend endpoints available" : connection === "outdated" ? "Backend is out of date — submissions disabled" : "Backend unavailable — check network and deployment"}
      </p>
      <div className="flex gap-4"><button onClick={() => { setProbe((value) => value + 1); router.refresh(); }} className="text-accent">Refresh</button><button aria-expanded={settingsOpen} onClick={() => setSettingsOpen(!settingsOpen)} className="text-accent">Connection settings</button></div>
    </div>
    {connection === "outdated" && <div role="alert" className="mx-6 mt-4 rounded-lg border border-accent-amber/40 bg-bg-card p-4 text-sm text-accent-amber">This API is missing the merged intake, mapping or planning endpoints. Existing records may contain historical demo fields. New uploads and runs are blocked until the backend is updated and you refresh. A successful connection is not scientific validation.</div>}
    {settingsOpen && <form className="mx-6 my-4 rounded-lg border border-border bg-bg-card p-5" onSubmit={(event) => {
      event.preventDefault();
      try {
        const saved = saveApiUrl(draft);
        setEndpoint(saved.url);
        setProbe((value) => value + 1);
        setMessage(saved.persisted ? "Connection saved. Checking the backend…" : "Using this connection for this session; storage is unavailable.");
        router.refresh();
      } catch (error) { setMessage(error instanceof Error ? error.message : "Invalid backend address"); }
    }}>
      <label className="block text-sm font-semibold" htmlFor="backend-url">Backend address</label>
      <div className="mt-3 flex gap-3"><input id="backend-url" type="url" required value={draft} onChange={(event) => setDraft(event.target.value)} className="min-w-0 flex-1 rounded border border-border bg-bg px-3 py-2" /><button className="rounded bg-accent px-4 py-2 text-bg">Save and test</button></div>
      <p className="mt-3 text-xs text-muted">Only the approved CasAI deployment is allowed. No API keys belong here. Processing needs internet access; use public or synthetic demo inputs only.</p>
      {message && <p role="status" className="mt-3 text-sm text-text-secondary">{message}</p>}
    </form>}
    {loadedKey === key ? content : <section role="status" className="p-8 text-text-secondary">Loading workspace…</section>}
  </SiteShell>;
}
