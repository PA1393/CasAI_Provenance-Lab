"use client";

import { useEffect, useRef, useState } from "react";
import { createPluginUI } from "molstar/lib/mol-plugin-ui";
import { renderReact18 } from "molstar/lib/mol-plugin-ui/react18";
import { DefaultPluginUISpec } from "molstar/lib/mol-plugin-ui/spec";
import { PluginUIContext } from "molstar/lib/mol-plugin-ui/context";
import type { StateObjectSelector } from "molstar/lib/mol-state";
import { Vec3 } from "molstar/lib/mol-math/linear-algebra";
import { Color } from "molstar/lib/mol-util/color/color";
import { PluginCommands } from "molstar/lib/mol-plugin/commands";
import "molstar/build/viewer/molstar.css";

// Deposited reference coordinates, not a predicted complex for the user's edit.
// Optional phase colors and camera rotation never alter atomic coordinates.

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

// Mirrors the theme tokens in tailwind.config.ts — Mol* needs literals. Nucleic
// acid and the engaged protein stay in the monochrome/green range; the warm
// tone is reserved for the post-edit state so it reads as the one change.
const NUCLEIC_COLOR = Color.fromHexStyle("#3dd68c");
const SURFACE_ENGAGE_COLOR = Color.fromHexStyle("#3d4a43");
const SURFACE_EDIT_COLOR = Color.fromHexStyle("#e8a04a");
const STICK_EDIT_COLOR = Color.fromHexStyle("#e8a04a");

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
    await plugin.build().delete(refs.surfaceRepr).commit();
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
    await plugin.build().delete(refs.stickRepr).commit();
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
  const [illustrativeColors, setIllustrativeColors] = useState(false);
  const stylePhase = illustrativeColors ? phase : 0;
  const phaseRef = useRef(stylePhase);
  const styleQueueRef = useRef<Promise<void>>(Promise.resolve());
  phaseRef.current = stylePhase;

  const safePdbId = pdbId && /^[A-Za-z0-9]{4}$/.test(pdbId) ? pdbId.toUpperCase() : null;
  const options = safePdbId
    ? [{ id: safePdbId, label: `User-supplied PDB ID (${safePdbId})` }, ...CRISPR_STRUCTURES.filter((item) => item.id !== safePdbId)]
    : CRISPR_STRUCTURES;
  // Default to the CRISPR complex so the enzyme is always present.
  const [structure, setStructure] = useState(CRISPR_STRUCTURES[0].id);
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");
  const [retryCount, setRetryCount] = useState(0);
  const [proteinVisible, setProteinVisible] = useState(true);
  const [nucleicVisible, setNucleicVisible] = useState(true);
  const [spinning, setSpinning] = useState(false);
  const [controlNotice, setControlNotice] = useState<string | null>(null);
  const [diagnostic, setDiagnostic] = useState("");
  const [elementCount, setElementCount] = useState(0);

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
      spec: { ...DefaultPluginUISpec(), layout: { initial: { isExpanded: false, showControls: false } } },
    }).then(async (plugin) => {
      if (cancelled) {
        plugin.dispose();
        throw new Error("Molecule3D unmounted before plugin finished initializing");
      }
      pluginInstance = plugin;
      await plugin.canvas3dInitialized;
      if (!plugin.canvas3d) throw new Error("WebGL molecular renderer was not initialized");
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
  }, [retryCount]);

  // Build / rebuild the scene when the chosen structure changes.
  useEffect(() => {
    const generation = ++generationRef.current;
    let active = true;
    setStatus("loading");
    setDiagnostic("");

    (async () => {
      const promise = pluginPromiseRef.current;
      if (!promise) return;

      let plugin: PluginUIContext;
      try {
        plugin = await promise;
      } catch (error) {
        if (active && generation === generationRef.current) {
          setStatus("error");
          setDiagnostic(error instanceof Error ? error.message.slice(0, 300) : "Renderer initialization failed");
        }
        return;
      }
      if (!active || generation !== generationRef.current) return;

      try {
        await styleQueueRef.current;
        if (!active || generation !== generationRef.current) return;
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
        setElementCount(structureObj.obj?.data.elementCount ?? 0);

        const refs = await buildComponents(plugin, structureObj);
        if (!active || generation !== generationRef.current) return;
        refsRef.current = refs;
        setProteinVisible(true);
        setNucleicVisible(true);
        setSpinning(false);

        await applyPhaseStyle(plugin, refs, phaseRef.current);
        if (!active || generation !== generationRef.current) return;
        const broken = Array.from(plugin.state.data.cells.values()).find(cell => cell.status === "error");
        if (broken) throw new Error(broken.errorText || "Structure representation failed");
        if (!structureObj.obj?.data.elementCount) throw new Error("The reference contained no renderable elements");
        // Representation commits are otherwise deferred to the animation loop.
        // WKWebView can suspend that loop while an expanded dialog is loading;
        // flush before checking readiness rather than reporting a false failure.
        plugin.canvas3d?.commit(true);
        if (!plugin.canvas3d?.reprCount.value) throw new Error("The renderer did not create a molecular representation");

        plugin.managers.camera.reset();
        plugin.canvas3d?.setProps({
          renderer: { backgroundColor: Color.fromHexStyle("#0b1220") },
          trackball: { animate: { name: "off", params: {} } },
        });

        setStatus("ready");
      } catch (error) {
        if (active && generation === generationRef.current) {
          setStatus("error");
          setDiagnostic(error instanceof Error ? error.message.slice(0, 300) : "Structure loading failed");
        }
      }
    })();

    return () => {
      active = false;
    };
  }, [structure, retryCount]);

  // Re-style on phase changes (no reload).
  useEffect(() => {
    if (status !== "ready") return;
    const plugin = pluginPromiseRef.current;
    const refs = refsRef.current;
    if (!plugin || !refs) return;
    let active = true;
    styleQueueRef.current = styleQueueRef.current.catch(() => {}).then(async () => {
      const p = await plugin;
      if (active && refsRef.current === refs) await applyPhaseStyle(p, refs, stylePhase);
    }).catch(() => {
      if (active && refsRef.current === refs) setStatus("error");
    });
    return () => { active = false; };
  }, [stylePhase, status]);

  async function control(action: (plugin: PluginUIContext) => void | Promise<void>) {
    const promise = pluginPromiseRef.current;
    if (!promise || status !== "ready") return;
    try { await action(await promise); setControlNotice(null); }
    catch { setControlNotice("That view control was unavailable. The stored run was not changed."); }
  }

  function togglePart(part: "protein" | "nucleic") {
    void control(async plugin => {
      const ref = refsRef.current?.[part];
      if (!ref) { setControlNotice("This reference has no matching component."); return; }
      await PluginCommands.State.ToggleVisibility(plugin, { state: plugin.state.data, ref: ref.ref });
      if (part === "protein") setProteinVisible(value => !value);
      else setNucleicVisible(value => !value);
    });
  }

  return (
    <div className="relative flex h-full w-full flex-col overflow-hidden rounded-lg">

      <div className="flex flex-wrap items-center gap-2 border-b border-border bg-bg-card p-2">
        <select
          aria-label="Public example structure"
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
        <button type="button" disabled={status !== "ready"} onClick={() => void control(plugin => { plugin.managers.camera.reset(); })} className="rounded border border-border px-2 py-1 text-xs disabled:opacity-40">Reset camera</button>
        <button type="button" disabled={status !== "ready"} aria-pressed={proteinVisible} onClick={() => togglePart("protein")} className="rounded border border-border px-2 py-1 text-xs disabled:opacity-40">Protein {proteinVisible ? "on" : "off"}</button>
        <button type="button" disabled={status !== "ready"} aria-pressed={nucleicVisible} onClick={() => togglePart("nucleic")} className="rounded border border-border px-2 py-1 text-xs disabled:opacity-40">DNA / RNA {nucleicVisible ? "on" : "off"}</button>
        <button type="button" disabled={status !== "ready"} aria-pressed={spinning} onClick={() => void control(plugin => {
          plugin.canvas3d?.setProps({ trackball: { animate: spinning ? { name: "off", params: {} } : { name: "spin", params: { speed: 1, axis: Vec3.create(0, 1, 0) } } } });
          setSpinning(value => !value);
        })} className="rounded border border-border px-2 py-1 text-xs disabled:opacity-40">{spinning ? "Stop rotation" : "Rotate view"}</button>
        <label className="flex items-center gap-2 text-xs"><input type="checkbox" checked={illustrativeColors} onChange={event => setIllustrativeColors(event.target.checked)} />Illustrative phase colors</label>
      </div>
      <p className="px-3 py-2 text-xs text-muted">Drag to orbit · scroll to zoom · hover or click atoms/residues to inspect. Rotation and phase colors are presentation controls, not molecular motion.</p>
      {status === "ready" && <p role="status" className="px-3 pb-2 text-xs text-muted">Reference {structure} · {elementCount.toLocaleString()} structure elements</p>}
      {controlNotice && <p role="status" className="px-3 text-xs text-muted">{controlNotice}</p>}
      <div ref={containerRef} className="relative min-h-0 flex-1" />

      {status === "loading" && (
        <div className="absolute inset-0 z-0 flex items-center justify-center font-mono text-xs text-muted">
          Loading structure {structure}…
        </div>
      )}
      {status === "error" && (
        <div className="absolute inset-0 z-20 flex flex-col items-center justify-center gap-2 bg-bg/80 px-6 text-center font-mono text-xs text-accent-red">
          <span>Could not load the 3D structure.</span>
          <span className="text-muted">Check your internet connection (structures stream from RCSB).</span>
          {diagnostic && <details className="text-xs text-muted"><summary>Viewer diagnostic</summary><p>{diagnostic}</p></details>}
          <button
            onClick={() => setRetryCount((count) => count + 1)}
            className="mt-1 rounded border border-border px-3 py-1 text-text hover:border-accent"
          >
            Retry
          </button>
        </div>
      )}
    </div>
  );
}
