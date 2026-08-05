"use client";

import { useEffect, useRef, useState } from "react";
import { createPluginUI } from "molstar/lib/mol-plugin-ui";
import { renderReact18 } from "molstar/lib/mol-plugin-ui/react18";
import { DefaultPluginUISpec } from "molstar/lib/mol-plugin-ui/spec";
import { PluginUIContext } from "molstar/lib/mol-plugin-ui/context";
import type { StateObjectSelector } from "molstar/lib/mol-state";
import { Vec3 } from "molstar/lib/mol-math/linear-algebra";
import { Color } from "molstar/lib/mol-util/color/color";
import "molstar/build/viewer/molstar.css";

// 3D molecular viewer for the CRISPR edit. Renders a real Cas9–sgRNA–DNA
// complex from the PDB via Mol*. The structure spins continuously and
// re-styles per simulation phase so the "enzyme" is visibly engaging the
// DNA as the edit proceeds.

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

const NUCLEIC_COLOR = Color.fromHexStyle("#38bdf8");
const SURFACE_ENGAGE_COLOR = Color.fromHexStyle("#a78bfa");
const SURFACE_EDIT_COLOR = Color.fromHexStyle("#fb923c");
const STICK_EDIT_COLOR = Color.fromHexStyle("#fb923c");

interface StructureRefs {
  structure: StateObjectSelector;
  protein?: StateObjectSelector;
  nucleic?: StateObjectSelector;
  stickRepr?: StateObjectSelector;
  surfaceRepr?: StateObjectSelector;
}

// Rebuilds the phase-dependent parts only (nucleic stick color + protein
// surface). The base cartoon representations are built once per structure
// load and left alone — matches the original's visual result without
// tearing down parts of the scene that don't depend on phase.
async function applyPhaseStyle(plugin: PluginUIContext, refs: StructureRefs, phase: number) {
  if (refs.surfaceRepr) {
    plugin.build().delete(refs.surfaceRepr).commit();
    refs.surfaceRepr = undefined;
  }
  if (phase >= 2 && refs.protein) {
    refs.surfaceRepr = await plugin.builders.structure.representation.addRepresentation(refs.protein, {
      type: "molecular-surface",
      typeParams: { alpha: 0.35 },
      color: "uniform",
      colorParams: { value: phase >= 3 ? SURFACE_EDIT_COLOR : SURFACE_ENGAGE_COLOR },
    });
  }

  if (refs.stickRepr) {
    plugin.build().delete(refs.stickRepr).commit();
    refs.stickRepr = undefined;
  }
  if (refs.nucleic) {
    refs.stickRepr = await plugin.builders.structure.representation.addRepresentation(refs.nucleic, {
      type: "ball-and-stick",
      typeParams: phase >= 3 ? { sizeFactor: 0.22 } : undefined,
      color: phase >= 3 ? "uniform" : "element-symbol",
      colorParams: phase >= 3 ? { value: STICK_EDIT_COLOR } : undefined,
    });
  }
}

async function buildComponents(plugin: PluginUIContext, structure: StateObjectSelector): Promise<StructureRefs> {
  const refs: StructureRefs = { structure };

  refs.protein = await plugin.builders.structure.tryCreateComponentStatic(structure, "protein", {
    label: "Protein",
  });
  if (refs.protein) {
    await plugin.builders.structure.representation.addRepresentation(refs.protein, {
      type: "cartoon",
      color: "sequence-id",
    });
  }

  refs.nucleic = await plugin.builders.structure.tryCreateComponentStatic(structure, "nucleic", {
    label: "Nucleic acid",
  });
  if (refs.nucleic) {
    await plugin.builders.structure.representation.addRepresentation(refs.nucleic, {
      type: "cartoon",
      color: "uniform",
      colorParams: { value: NUCLEIC_COLOR },
    });
  }

  return refs;
}

export function Molecule3D({ phase, pdbId }: Props) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const pluginPromiseRef = useRef<Promise<PluginUIContext> | null>(null);
  const refsRef = useRef<StructureRefs | null>(null);
  const generationRef = useRef(0);
  const phaseRef = useRef(phase);
  phaseRef.current = phase;

  const options = pdbId
    ? [{ id: pdbId, label: `Research-object structure (${pdbId})` }, ...CRISPR_STRUCTURES]
    : CRISPR_STRUCTURES;
  // Default to the CRISPR complex so the enzyme is always present.
  const [structure, setStructure] = useState(CRISPR_STRUCTURES[0].id);
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");

  // Plugin lifecycle: created once per mount, disposed once on unmount.
  // React StrictMode double-invokes this effect in dev, and the two
  // invocations can overlap in-flight (createPluginUI is async). Giving
  // each mount attempt its own child node means two concurrent attempts
  // target two different DOM nodes, so they can never collide on a single
  // `createRoot()` call.
  useEffect(() => {
    const parent = containerRef.current;
    if (!parent) return;

    const mountNode = document.createElement("div");
    mountNode.style.position = "absolute";
    mountNode.style.inset = "0";
    parent.appendChild(mountNode);

    let cancelled = false;
    let pluginInstance: PluginUIContext | null = null;

    const promise = createPluginUI({
      target: mountNode,
      render: renderReact18,
      spec: DefaultPluginUISpec(),
    }).then((plugin) => {
      if (cancelled) {
        plugin.dispose();
        throw new Error("Molecule3D unmounted before plugin finished initializing");
      }
      pluginInstance = plugin;
      return plugin;
    });

    pluginPromiseRef.current = promise;

    return () => {
      cancelled = true;
      pluginPromiseRef.current = null;
      refsRef.current = null;
      mountNode.remove();
      pluginInstance?.dispose();
    };
  }, []);

  // Build / rebuild the scene when the chosen structure changes.
  useEffect(() => {
    const generation = ++generationRef.current;
    let active = true;
    setStatus("loading");

    (async () => {
      const promise = pluginPromiseRef.current;
      if (!promise) return;

      let plugin: PluginUIContext;
      try {
        plugin = await promise;
      } catch {
        return;
      }
      if (!active || generation !== generationRef.current) return;

      try {
        await plugin.clear();
        if (!active || generation !== generationRef.current) return;

        const data = await plugin.builders.data.download(
          { url: `https://files.rcsb.org/download/${structure}.pdb`, isBinary: false },
          { state: { isGhost: true } },
        );
        if (!active || generation !== generationRef.current) return;

        const trajectory = await plugin.builders.structure.parseTrajectory(data, "pdb");
        if (!active || generation !== generationRef.current) return;

        const model = await plugin.builders.structure.createModel(trajectory);
        if (!active || generation !== generationRef.current) return;

        const structureObj = await plugin.builders.structure.createStructure(model);
        if (!active || generation !== generationRef.current) return;

        const refs = await buildComponents(plugin, structureObj);
        if (!active || generation !== generationRef.current) return;
        refsRef.current = refs;

        await applyPhaseStyle(plugin, refs, phaseRef.current);
        if (!active || generation !== generationRef.current) return;

        plugin.managers.camera.reset();
        plugin.canvas3d?.setProps({
          trackball: { animate: { name: "spin", params: { speed: 1, axis: Vec3.create(0, 1, 0) } } },
        });

        setStatus("ready");
      } catch {
        if (active && generation === generationRef.current) setStatus("error");
      }
    })();

    return () => {
      active = false;
    };
  }, [structure]);

  // Re-style on phase changes (no reload).
  useEffect(() => {
    if (status !== "ready") return;
    const plugin = pluginPromiseRef.current;
    const refs = refsRef.current;
    if (!plugin || !refs) return;
    plugin.then((p) => {
      if (refsRef.current === refs) applyPhaseStyle(p, refs, phase);
    });
  }, [phase, status]);

  return (
    <div className="relative h-full w-full overflow-hidden rounded-lg">
      <div ref={containerRef} className="absolute inset-0" />

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
          <span className="text-muted">Check your internet connection (structures stream from RCSB).</span>
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
