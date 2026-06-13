"use client";

import { useEffect, useRef } from "react";

// Animated 2D schematic of a CRISPR base-editing event on a DNA double helix.
// Phases (driven by the parent timeline):
//   0 SCAN  - Cas9 slides along the helix searching for the PAM
//   1 BIND  - guide RNA base-pairs with the target strand (R-loop opens)
//   2 CUT   - nuclease/deaminase acts at the target base
//   3 EDIT  - target base is converted (C->T), edit locked in

type Props = {
  phase: number;
  guideRna?: string | null;
};

const COLORS = {
  bg: "#0c0f13",
  strandA: "#5eead4",
  strandB: "#38bdf8",
  rung: "#1f2a33",
  cas9: "#a78bfa",
  cas9Core: "#7c3aed",
  guide: "#fbbf24",
  editFrom: "#38bdf8",
  editTo: "#fb923c",
  text: "#7a8794",
};

export function Molecule2D({ phase, guideRna }: Props) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const phaseRef = useRef(phase);
  phaseRef.current = phase;

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let raf = 0;
    let start = performance.now();

    function resize() {
      const c = canvasRef.current;
      if (!c) return;
      const ratio = window.devicePixelRatio || 1;
      const w = c.clientWidth;
      const h = c.clientHeight;
      c.width = Math.max(1, Math.floor(w * ratio));
      c.height = Math.max(1, Math.floor(h * ratio));
      ctx!.setTransform(ratio, 0, 0, ratio, 0, 0);
    }
    resize();
    window.addEventListener("resize", resize);

    function draw(now: number) {
      const c = canvasRef.current;
      if (!c || !ctx) return;
      const W = c.clientWidth;
      const H = c.clientHeight;
      const t = (now - start) / 1000;
      const ph = phaseRef.current;

      ctx.clearRect(0, 0, W, H);
      ctx.fillStyle = COLORS.bg;
      ctx.fillRect(0, 0, W, H);

      const midY = H / 2;
      const amp = Math.min(46, H * 0.22);
      const wl = 70; // wavelength
      const margin = 28;
      const targetX = W * 0.56; // where the edit happens
      const rloop = ph >= 1; // strands separate at target during/after bind

      // helper: vertical separation factor near the target (R-loop bubble)
      function sep(x: number) {
        if (!rloop) return 0;
        const d = Math.abs(x - targetX);
        const width = 70;
        if (d > width) return 0;
        const k = Math.cos((d / width) * (Math.PI / 2));
        return k * k * 26;
      }

      // base-pair rungs
      for (let x = margin; x <= W - margin; x += 14) {
        const s = sep(x);
        const yA = midY - amp * Math.sin((x + t * 40) / wl * Math.PI) - s;
        const yB = midY + amp * Math.sin((x + t * 40) / wl * Math.PI) + s;
        ctx.strokeStyle = COLORS.rung;
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(x, yA);
        ctx.lineTo(x, yB);
        ctx.stroke();
      }

      // two backbones
      function backbone(offset: number, color: string, dir: number) {
        ctx!.strokeStyle = color;
        ctx!.lineWidth = 3.5;
        ctx!.beginPath();
        for (let x = margin; x <= W - margin; x += 4) {
          const s = sep(x) * dir;
          const y = midY + dir * amp * Math.sin((x + t * 40) / wl * Math.PI) + s + offset;
          if (x === margin) ctx!.moveTo(x, y);
          else ctx!.lineTo(x, y);
        }
        ctx!.stroke();
      }
      backbone(0, COLORS.strandA, -1);
      backbone(0, COLORS.strandB, 1);

      // guide RNA strand pairing into the bottom (target) strand during BIND+
      if (ph >= 1) {
        const reveal = Math.min(1, (t % 100) > 0 ? 1 : 1); // fully shown once bound
        ctx.strokeStyle = COLORS.guide;
        ctx.lineWidth = 3;
        ctx.setLineDash([6, 4]);
        ctx.beginPath();
        const gw = 70 * reveal;
        for (let x = targetX - gw; x <= targetX + gw; x += 4) {
          const y = midY + amp * Math.sin((x + t * 40) / wl * Math.PI) + sep(x) + 7;
          if (x === targetX - gw) ctx.moveTo(x, y);
          else ctx.lineTo(x, y);
        }
        ctx.stroke();
        ctx.setLineDash([]);
      }

      // target base pair (the one being edited)
      const baseYA = midY - amp * Math.sin((targetX + t * 40) / wl * Math.PI) - sep(targetX);
      const baseYB = midY + amp * Math.sin((targetX + t * 40) / wl * Math.PI) + sep(targetX);
      const edited = ph >= 3;
      const editing = ph === 2;
      const baseColor = edited
        ? COLORS.editTo
        : editing
          ? (Math.sin(t * 12) > 0 ? COLORS.editTo : COLORS.editFrom)
          : COLORS.editFrom;
      for (const [y, label] of [
        [baseYA, edited ? "T" : "C"],
        [baseYB, edited ? "A" : "G"],
      ] as [number, string][]) {
        ctx.fillStyle = baseColor;
        ctx.beginPath();
        ctx.arc(targetX, y, 8, 0, Math.PI * 2);
        ctx.fill();
        ctx.fillStyle = "#06080a";
        ctx.font = "bold 10px monospace";
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        ctx.fillText(label, targetX, y);
      }

      // Cas9 enzyme: slides in during SCAN, parks over target afterwards
      const enter = Math.min(1, t / 1.4);
      const scanX = ph === 0
        ? margin + 40 + (targetX - margin - 40) * (0.5 + 0.5 * Math.sin(t * 1.6)) * enter
        : targetX;
      const pulse = ph === 2 ? 1 + 0.08 * Math.sin(t * 14) : 1;
      const rx = 52 * pulse;
      const ry = 40 * pulse;
      ctx.save();
      ctx.globalAlpha = 0.18;
      ctx.fillStyle = COLORS.cas9;
      ctx.beginPath();
      ctx.ellipse(scanX, midY, rx, ry, 0, 0, Math.PI * 2);
      ctx.fill();
      ctx.restore();
      ctx.strokeStyle = COLORS.cas9;
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.ellipse(scanX, midY, rx, ry, 0, 0, Math.PI * 2);
      ctx.stroke();
      // bilobed core
      ctx.fillStyle = COLORS.cas9Core;
      ctx.globalAlpha = 0.5;
      ctx.beginPath();
      ctx.ellipse(scanX - 16, midY - 6, 18, 16, 0, 0, Math.PI * 2);
      ctx.ellipse(scanX + 16, midY + 6, 18, 16, 0, 0, Math.PI * 2);
      ctx.fill();
      ctx.globalAlpha = 1;
      ctx.fillStyle = "#ede9fe";
      ctx.font = "bold 9px monospace";
      ctx.fillText("Cas9", scanX, midY);

      raf = requestAnimationFrame(draw);
    }

    raf = requestAnimationFrame(draw);
    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener("resize", resize);
    };
  }, []);

  return (
    <div className="relative h-full w-full">
      <canvas ref={canvasRef} className="h-full w-full rounded-lg" />
      {guideRna && (
        <div className="pointer-events-none absolute bottom-2 left-3 font-mono text-[10px] text-muted">
          guide: <span className="text-[#fbbf24]">{guideRna}</span>
        </div>
      )}
    </div>
  );
}
