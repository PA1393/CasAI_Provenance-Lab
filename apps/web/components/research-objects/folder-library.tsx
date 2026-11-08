"use client";
import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { createFolder, getFolders, getResearchObjects, getRuns, placeInFolder, type ResearchFolder, type ResearchObject, type Run } from "../../lib/api/client";

export function FolderLibrary() {
  const [folders, setFolders] = useState<ResearchFolder[]>([]);
  const [inputs, setInputs] = useState<ResearchObject[]>([]);
  const [runs, setRuns] = useState<Run[]>([]);
  const [selected, setSelected] = useState("all");
  const [name, setName] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [ready, setReady] = useState(false);
  const refresh = useCallback(async () => {
    const [f, i, r] = await Promise.all([getFolders(), getResearchObjects(), getRuns()]);
    setFolders(f); setInputs(i); setRuns(r); setReady(true);
  }, []);
  useEffect(() => { let active = true;
    Promise.all([getFolders(), getResearchObjects(), getRuns()]).then(([f, i, r]) => {
      if (active) { setFolders(f); setInputs(i); setRuns(r); setReady(true); }
    }, () => { if (active) setError("Your folders could not be loaded. Check your session and deployment."); });
    return () => { active = false; };
  }, []);
  async function move(kind: "input" | "run", id: string, folder: string) {
    setBusy(true); setError("");
    try { await placeInFolder(kind, id, folder || null); await refresh(); }
    catch { setError("The move could not be confirmed. Refresh before trying again."); }
    finally { setBusy(false); }
  }
  const records = [
    ...inputs.map(input => ({ id: input.research_object_id, title: input.name, folder: input.folder_id, kind: "input" as const, url: `/research-objects/${input.research_object_id}` })),
    ...runs.map(run => ({ id: run.run_id, title: run.prompt, folder: run.folder_id, kind: "run" as const, url: `/runs/${run.run_id}` })),
  ].filter(record => selected === "all" || (selected === "unfiled" ? !record.folder : record.folder === selected));
  return <section className="mx-auto max-w-6xl px-6 py-10">
    <h1 className="font-serif-display text-4xl">Your research folders</h1>
    <p className="mt-3 text-sm text-text-secondary">Create project folders and move inputs and runs independently. Moving a run never changes its source or provenance.</p>
    <form className="mt-7 flex flex-wrap gap-3" onSubmit={async event => {
      event.preventDefault(); if (busy || !name.trim()) return; setBusy(true); setError("");
      try { await createFolder(name.trim()); setName(""); await refresh(); }
      catch { setError("Folder creation could not be confirmed. Refresh before retrying."); }
      finally { setBusy(false); }
    }}>
      <label className="sr-only" htmlFor="folder-name">New folder name</label>
      <input id="folder-name" required maxLength={100} value={name} disabled={busy} onChange={e => setName(e.target.value)} placeholder="Project folder name" className="rounded-lg border border-border bg-bg-card p-3" />
      <button disabled={busy || !ready || !name.trim()} className="rounded-lg bg-accent px-5 py-3 text-bg disabled:opacity-40">Create folder</button>
    </form>
    {error && <p role="alert" className="mt-4 text-accent-amber">{error}</p>}
    <label className="mt-7 block text-sm">Show folder<select value={selected} onChange={e => setSelected(e.target.value)} className="ml-3 rounded-lg border border-border bg-bg-card p-2"><option value="all">All my research</option><option value="unfiled">Unfiled</option>{folders.map(folder => <option key={folder.folder_id} value={folder.folder_id}>{folder.name}</option>)}</select></label>
    <div className="mt-5 grid gap-3">{records.map(record => <article key={record.kind + record.id} className="flex flex-wrap items-center justify-between gap-4 rounded-xl border border-border bg-bg-card p-5">
      <Link href={record.url} className="min-w-0 break-words text-accent">{record.title}<span className="ml-3 text-xs text-muted">{record.kind}</span></Link>
      <label className="text-xs">Move to <select aria-label={`Folder for ${record.title}`} disabled={busy} value={record.folder || ""} onChange={e => move(record.kind, record.id, e.target.value)} className="ml-2 rounded border border-border bg-bg p-2"><option value="">Unfiled</option>{folders.map(folder => <option key={folder.folder_id} value={folder.folder_id}>{folder.name}</option>)}</select></label>
    </article>)}</div>
    {ready && records.length === 0 && <p className="mt-6 text-sm text-muted">No research in this view yet. <Link href="/research-objects/new" className="text-accent">Add research</Link></p>}
  </section>;
}
