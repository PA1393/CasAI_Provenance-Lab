"use client";

import { useEffect, useRef, useState } from "react";
import { Molecule2D } from "@/components/runs/simulation/molecule-2d";
import { Molecule3D } from "@/components/runs/simulation/molecule-3d";

type Props = {
  pdbId?: string | null;
  guideRna?: string | null;
  editedSequence?: string | null;
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
    desc: "The base is converted (C→T) — the edit is locked into the sequence.",
  },
];

const STEP_MS = 2800;

export function RunSimulation({ pdbId, guideRna, editedSequence }: Props) {
  const [phase, setPhase] = useState(0);
  const [playing, setPlaying] = useState(true);
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
    <div className="flex flex-col gap-5">
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

      <div className="grid gap-5 lg:grid-cols-2">
        <figure className="flex flex-col rounded-lg border border-border bg-bg-card">
          <figcaption className="flex items-center justify-between border-b border-border px-4 py-2 font-mono text-[10px] tracking-[0.2em] uppercase text-muted">
            <span>2D · Edit mechanism</span>
            <span className="text-accent">live</span>
          </figcaption>
          <div className="h-[300px] p-2">
            <Molecule2D phase={phase} guideRna={guideRna} />
          </div>
        </figure>

        <figure className="flex flex-col rounded-lg border border-border bg-bg-card">
          <figcaption className="flex items-center justify-between border-b border-border px-4 py-2 font-mono text-[10px] tracking-[0.2em] uppercase text-muted">
            <span>3D · Molecular structure</span>
            <span className="text-accent">drag to rotate</span>
          </figcaption>
          <div className="h-[300px] p-2">
            <Molecule3D phase={phase} pdbId={pdbId} />
          </div>
        </figure>
      </div>

      {editedSequence && (
        <div className="rounded-lg border border-border bg-bg-card px-5 py-4">
          <p className="font-mono text-[10px] tracking-[0.2em] uppercase text-muted font-semibold">
            Resulting edited sequence
          </p>
          <p className="mt-2 font-mono text-xs text-[#fb923c] break-all">{editedSequence}</p>
        </div>
      )}
    </div>
  );
}
