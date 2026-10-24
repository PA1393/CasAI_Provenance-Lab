"use client";

import { useEffect, useRef, useState } from "react";
import { Molecule2D } from "@/components/runs/simulation/molecule-2d";
import { CasaiScene } from "./casai-scene";
import { ReferenceStructurePanel } from "./reference-structure-panel";
import {
  SequenceTrack,
  type EditGeometry,
} from "@/components/runs/simulation/sequence-track";


type Props = {
  pdbId?: string | null;
  guideRna?: string | null;
  editedSequence?: string | null;
  sequence?: string | null;
  geometry?: EditGeometry | null;
};

const PHASES = [
  {
    key: "scan",
    label: "SCAN",
    desc: "Cas9 slides along the DNA, probing for a PAM next to the target site.",
  },
  {
    key: "bind",
    label: "BIND",
    desc: "The guide RNA base-pairs with the target strand, opening an R-loop.",
  },
  {
    key: "cut",
    label: "ACT",
    desc: "The nuclease/deaminase domain engages and acts on the target base.",
  },
  {
    key: "edit",
    label: "EDIT",
    desc: "Compare the computed sequence with the supplied input when a result is available.",
  },
];

const STEP_MS = 2800;

export function RunSimulation({
  pdbId,
  guideRna,
  editedSequence,
  sequence,
  geometry,
}: Props) {
  const [phase, setPhase] = useState(0);
  const [playing, setPlaying] = useState(false);
  const timer = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (!playing) {
      if (timer.current) clearInterval(timer.current);
      return;
    }
    timer.current = setInterval(() => {
      setPhase((p) => (p + 1) % PHASES.length);
    }, STEP_MS);
    return () => {
      if (timer.current) clearInterval(timer.current);
    };
  }, [playing]);

  const current = PHASES[phase];

  return (
    // The console is the one dark surface in the application. Everything the
    // pipeline actually renders — the sequence readout, the helix, the
    // structure — was designed as green-on-black instrumentation, and setting
    // it into the warm clinical page the way a real bench instrument sits on a
    // bench reads far better than tinting the whole product dark. The
    // `instrument` class swaps the palette for this subtree (see globals.css);
    // nothing inside needs to know which context it renders into.
    <div className="flex flex-col gap-5 rounded-xl border border-border bg-bg-card p-5">
      <p className="rounded-lg bg-accent-soft px-4 py-3 text-sm text-text-secondary">Built on supplied sequences, recorded edit computations and optional public structures. The interaction is illustrative, not a validated enzyme trajectory or experimental outcome.</p>
      {/* phase timeline */}
      <div className="flex items-center gap-2">
        {PHASES.map((p, i) => (
          <button
            key={p.key}
            onClick={() => {
              setPhase(i);
              setPlaying(false);
            }}
            className={`flex-1 rounded border px-3 py-2 font-mono text-[10px] tracking-[0.18em] uppercase transition-colors ${
              i === phase
                ? "border-accent bg-accent/10 text-accent"
                : i < phase
                  ? "border-border bg-bg-card text-text"
                  : "border-border/50 bg-bg-card/40 text-muted"
            }`}
          >
            {i + 1}. {p.label}
          </button>
        ))}
        <button
          onClick={() => setPlaying((v) => !v)}
          className="shrink-0 rounded border border-border bg-bg-card px-3 py-2 font-mono text-[10px] tracking-[0.18em] uppercase text-text hover:border-accent hover:text-accent"
        >
          {playing ? "Pause" : "Play"}
        </button>
      </div>

      <p className="font-mono text-xs text-muted">
        <span className="text-accent">{current.label}</span> — {current.desc}
      </p>

      <CasaiScene sequence={sequence} editedSequence={editedSequence} geometry={geometry} phase={phase} />

      {/* The real bases, annotated at their real coordinates — the mechanism
          panels below are schematic, this one is the run's actual output. */}
      <figure className="flex flex-col rounded-lg border border-border bg-bg-card">
        <figcaption className="flex items-center justify-between border-b border-border px-4 py-2 font-mono text-[10px] tracking-[0.2em] uppercase text-muted">
          <span>Sequence · Edit site</span>
          <span className="text-accent">
            {geometry?.strand ? `${geometry.strand} strand` : "no edit geometry"}
          </span>
        </figcaption>
        <div className="p-4">
          <SequenceTrack
            sequence={sequence}
            editedSequence={editedSequence}
            geometry={geometry}
            phase={phase}
          />
        </div>
      </figure>

      <div className="grid gap-5 lg:grid-cols-2">
        <figure className="flex flex-col rounded-lg border border-border bg-bg-card">
          <figcaption className="flex items-center justify-between border-b border-border px-4 py-2 font-mono text-[10px] tracking-[0.2em] uppercase text-muted">
            <span>2D · Edit mechanism</span>
            <span className="text-accent">schematic</span>
          </figcaption>
          <div className="h-[300px] p-2">
            <Molecule2D phase={phase} guideRna={guideRna} />
          </div>
        </figure>

        <ReferenceStructurePanel phase={phase} pdbId={pdbId} />
      </div>

      {editedSequence && (
        <div className="rounded-lg border border-border bg-bg-card px-5 py-4">
          <p className="font-mono text-[10px] tracking-[0.2em] uppercase text-muted font-semibold">
            Resulting edited sequence
          </p>
          <p className="mt-2 font-mono text-xs text-accent-amber break-all">{editedSequence}</p>
        </div>
      )}
    </div>
  );
}
