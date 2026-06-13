"use client";

import { useEffect, useRef, useState } from "react";

// 3D molecular viewer for the CRISPR edit. Uses 3Dmol.js (loaded from CDN) to
// render a real Cas9–sgRNA–DNA complex from the PDB. The structure spins
// continuously and re-styles per simulation phase so the "enzyme" is visibly
// engaging the DNA as the edit proceeds.

type Props = {
  phase: number;
  pdbId?: string | null;
};

// Curated structures that actually contain the CRISPR machinery.
const CRISPR_STRUCTURES = [
  { id: "4UN3", label: "SpCas9 · sgRNA · target DNA (4UN3)" },
  { id: "5F9R", label: "SpCas9 catalytic complex (5F9R)" },
  { id: "6VPC", label: "Base editor · Cas9 nickase (6VPC)" },
];

declare global {
  interface Window {
    // 3Dmol attaches itself here once the script loads.
    $3Dmol?: any;
  }
}

let scriptPromise: Promise<void> | null = null;
function load3Dmol(): Promise<void> {
  if (typeof window === "undefined") return Promise.reject();
  if (window.$3Dmol) return Promise.resolve();
  if (scriptPromise) return scriptPromise;
  scriptPromise = new Promise<void>((resolve, reject) => {
    const s = document.createElement("script");
    s.src = "https://3Dmol.org/build/3Dmol-min.js";
    s.async = true;
    s.onload = () => resolve();
    s.onerror = () => reject(new Error("Failed to load 3Dmol.js"));
    document.head.appendChild(s);
  });
  return scriptPromise;
}

export function Molecule3D({ phase, pdbId }: Props) {
  const hostRef = useRef<HTMLDivElement | null>(null);
  const viewerRef = useRef<any>(null);
  const phaseRef = useRef(phase);
  phaseRef.current = phase;

  const options = pdbId
    ? [{ id: pdbId, label: `Research-object structure (${pdbId})` }, ...CRISPR_STRUCTURES]
    : CRISPR_STRUCTURES;
  // Default to the CRISPR complex so the enzyme is always present.
  const [structure, setStructure] = useState(CRISPR_STRUCTURES[0].id);
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");

  function applyStyle(viewer: any, ph: number) {
    const $3Dmol = window.$3Dmol;
    if (!viewer || !$3Dmol) return;
    viewer.setStyle({}, {});
    // Protein (the Cas9 enzyme) as cartoon, spectrum-colored.
    viewer.setStyle(
      { resn: ["DA", "DC", "DG", "DT", "A", "C", "G", "U"], invert: true },
      { cartoon: { color: "spectrum" } },
    );
    // Nucleic acids (guide RNA + target DNA) as sticks so they read clearly.
    viewer.setStyle(
      { resn: ["DA", "DC", "DG", "DT", "A", "C", "G", "U"] },
      { stick: { colorscheme: "default", radius: 0.18 }, cartoon: { color: "#38bdf8" } },
    );
    // Engaging / editing phases: show the enzyme surface closing in, and
    // recolor the nucleic acids to signal the base conversion.
    viewer.removeAllSurfaces();
    if (ph >= 2) {
      viewer.addSurface($3Dmol.SurfaceType.VDW, {
        opacity: 0.35,
        color: ph >= 3 ? "#fb923c" : "#a78bfa",
      }, { resn: ["DA", "DC", "DG", "DT", "A", "C", "G", "U"], invert: true });
    }
    if (ph >= 3) {
      viewer.setStyle(
        { resn: ["DA", "DC", "DG", "DT", "A", "C", "G", "U"] },
        { stick: { color: "#fb923c", radius: 0.22 } },
      );
    }
    viewer.render();
  }

  // Build / rebuild the viewer when the chosen structure changes.
  useEffect(() => {
    let cancelled = false;
    setStatus("loading");

    load3Dmol()
      .then(() => {
        if (cancelled) return;
        const $3Dmol = window.$3Dmol;
        const host = hostRef.current;
        if (!$3Dmol || !host) return;

        if (!viewerRef.current) {
          viewerRef.current = $3Dmol.createViewer(host, {
            backgroundColor: "#0c0f13",
            antialias: true,
          });
        }
        const viewer = viewerRef.current;
        viewer.clear();

        $3Dmol.download(
          `pdb:${structure}`,
          viewer,
          { multimodel: false },
          () => {
            if (cancelled) return;
            applyStyle(viewer, phaseRef.current);
            viewer.zoomTo();
            viewer.spin("y", 1); // continuous rotation
            viewer.render();
            setStatus("ready");
          },
        );
      })
      .catch(() => {
        if (!cancelled) setStatus("error");
      });

    return () => {
      cancelled = true;
    };
  }, [structure]);

  // Re-style on phase changes (no reload).
  useEffect(() => {
    if (status === "ready" && viewerRef.current) {
      applyStyle(viewerRef.current, phase);
    }
  }, [phase, status]);

  return (
    <div className="relative h-full w-full overflow-hidden rounded-lg">
      <div ref={hostRef} className="absolute inset-0" style={{ position: "absolute" }} />

      <div className="absolute left-3 top-3 z-10">
        <select
          value={structure}
          onChange={(e) => setStructure(e.target.value)}
          className="rounded border border-border bg-bg/80 px-2 py-1 font-mono text-[10px] text-text backdrop-blur focus:border-accent focus:outline-none"
        >
          {options.map((o) => (
            <option key={o.id} value={o.id}>
              {o.label}
            </option>
          ))}
        </select>
      </div>

      {status === "loading" && (
        <div className="absolute inset-0 z-0 flex items-center justify-center font-mono text-xs text-muted">
          Loading structure {structure}…
        </div>
      )}
      {status === "error" && (
        <div className="absolute inset-0 z-20 flex flex-col items-center justify-center gap-2 bg-bg/80 px-6 text-center font-mono text-xs text-accent-red">
          <span>Could not load the 3D structure.</span>
          <span className="text-muted">Check your internet connection (structures stream from RCSB / 3Dmol.org).</span>
          <button
            onClick={() => setStructure((s) => s)}
            className="mt-1 rounded border border-border px-3 py-1 text-text hover:border-accent"
          >
            Retry
          </button>
        </div>
      )}
    </div>
  );
}
