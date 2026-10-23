"use client";

import { useEffect, useRef, useState } from "react";
import dynamic from "next/dynamic";
import { ViewerBoundary } from "./viewer-boundary";

const Molecule3D = dynamic(() => import("./molecule-3d").then(module => module.Molecule3D), { ssr: false });

export function ReferenceStructurePanel({ phase, pdbId }: { phase: number; pdbId?: string | null }) {
  const [loaded, setLoaded] = useState(false);
  const [expanded, setExpanded] = useState(false);
  const dialogRef = useRef<HTMLDialogElement>(null);
  const returnFocusRef = useRef<HTMLElement | null>(null);

  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;
    if (expanded) {
      returnFocusRef.current = document.activeElement as HTMLElement | null;
      dialog.close();
      dialog.showModal(); // Native top layer, focus trapping and background inertness.
    } else {
      dialog.close();
      dialog.show();
      returnFocusRef.current?.focus();
    }
    const frame = requestAnimationFrame(() => window.dispatchEvent(new Event("resize")));
    return () => cancelAnimationFrame(frame);
  }, [expanded]);

  return <figure className="min-w-0 rounded-lg border border-border bg-bg-card">
    <figcaption className="flex flex-wrap items-center justify-between gap-3 border-b border-border px-4 py-3 text-xs font-semibold">
      <span>3D · Molecular structure</span>
      <button type="button" onClick={() => setExpanded(true)} className="rounded border border-border-strong px-3 py-2 text-accent">Expand molecular viewer</button>
    </figcaption>
    <dialog ref={dialogRef} open aria-label="Molecular structure explorer" onCancel={event => { event.preventDefault(); setExpanded(false); }}
      className={expanded ? "fixed inset-4 m-auto flex h-[calc(100dvh-2rem)] w-[calc(100vw-2rem)] max-w-none flex-col rounded-xl border border-border bg-bg-card p-0 text-text backdrop:bg-black/70" : "relative m-0 block w-full max-w-none border-0 bg-bg-card p-0 text-text"}>
      {expanded && <header className="flex items-center justify-between gap-4 border-b border-border p-4"><h2 className="font-serif-display text-2xl">Molecular structure explorer</h2><button type="button" onClick={() => setExpanded(false)} className="rounded-lg border border-border-strong px-4 py-2 text-sm">Close viewer</button></header>}
      <div className={expanded ? "min-h-0 flex-1 p-2" : "h-[380px] p-2"}>
        {loaded ? <ViewerBoundary><Molecule3D phase={phase} pdbId={pdbId} /></ViewerBoundary> :
          <div className="flex h-full flex-col items-center justify-center gap-4 px-5 text-center">
            <p className="max-w-lg text-sm leading-6 text-text-secondary">Inspect a deposited public molecular structure with rotation, zoom and atom/residue selection. It is a reference complex, not a predicted structure for this run.</p>
            <button type="button" onClick={() => setLoaded(true)} className="rounded-lg border border-accent px-4 py-3 text-sm font-semibold text-accent">Load public 3D example</button>
          </div>}
      </div>
      <p className="border-t border-border px-4 py-3 text-xs leading-5 text-text-secondary">Reference coordinates from RCSB PDB. Spatial proximity is not proof of binding or catalytic activity. This viewer does not calculate molecular dynamics or modify deposited atoms to claim a gene edit.</p>
    </dialog>
  </figure>;
}
