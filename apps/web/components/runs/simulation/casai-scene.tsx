"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { complementBase, initialSceneStart, MAX_SCENE_BASES, sequenceScene } from "@/lib/scene-geometry";
import type { EditGeometry } from "./sequence-track";

type Props = { sequence?: string | null; editedSequence?: string | null; geometry?: EditGeometry | null; phase: number };
type Hit = { x: number; y: number; position: number };

export function CasaiScene({ sequence, editedSequence, geometry, phase }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const hitsRef = useRef<Hit[]>([]);
  const dragRef = useRef<{ x: number; y: number; distance: number } | null>(null);
  const [yaw, setYaw] = useState(-0.3);
  const [pitch, setPitch] = useState(0.3);
  const [zoom, setZoom] = useState(1);
  const [selected, setSelected] = useState<number | null>(null);
  const [windowStart, setWindowStart] = useState(() => initialSceneStart(sequence?.length ?? 0, geometry?.protospacerStart));
  const [renderError, setRenderError] = useState(false);
  const bases = useMemo(() => sequenceScene(sequence ?? "", editedSequence, windowStart, geometry?.protospacerStart), [sequence, editedSequence, windowStart, geometry?.protospacerStart]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) { setRenderError(true); return; }
    const draw = () => {
      const width = canvas.clientWidth, height = canvas.clientHeight;
      if (!width || !height) return;
      const ratio = Math.min(window.devicePixelRatio || 1, 2);
      canvas.width = Math.round(width * ratio); canvas.height = Math.round(height * ratio);
      ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
      ctx.fillStyle = "#0b1220"; ctx.fillRect(0, 0, width, height);
      const scale = Math.min(width / 26, height / 9) * zoom;
      const project = (x: number, y: number, z: number) => {
        const rx = x * Math.cos(yaw) + z * Math.sin(yaw);
        const rz = -x * Math.sin(yaw) + z * Math.cos(yaw);
        const ry = y * Math.cos(pitch) - rz * Math.sin(pitch);
        const depth = y * Math.sin(pitch) + rz * Math.cos(pitch);
        const perspective = 30 / (30 + depth);
        return { x: width / 2 + rx * scale * perspective, y: height / 2 + ry * scale * perspective, depth };
      };
      const projected = bases.map(base => ({ base, a: project(base.x, base.y, base.z), b: project(base.x, -base.y, -base.z) }));
      ctx.lineWidth = 1;
      for (const p of projected) {
        ctx.strokeStyle = p.base.guide ? "#337e70" : "#29394e";
        ctx.beginPath(); ctx.moveTo(p.a.x, p.a.y); ctx.lineTo(p.b.x, p.b.y); ctx.stroke();
      }
      for (const side of ["a", "b"] as const) {
        ctx.lineWidth = 2;
        ctx.strokeStyle = side === "a" ? "#2fc495" : "#8397b7";
        ctx.beginPath(); projected.forEach((p, i) => { if (i) ctx.lineTo(p[side].x, p[side].y); else ctx.moveTo(p[side].x, p[side].y); }); ctx.stroke();
      }
      const points = projected.flatMap(p => [{ ...p.a, base: p.base, reference: true }, { ...p.b, base: p.base, reference: false }]).sort((a, b) => b.depth - a.depth);
      for (const point of points) {
        const changed = point.reference && point.base.changed && phase >= 3;
        const radius = point.reference && point.base.position === selected ? 9 : 6;
        const color = changed ? "#f2be68" : point.reference ? "#2fc495" : "#8397b7";
        const glow = ctx.createRadialGradient(point.x - 2, point.y - 2, 0, point.x, point.y, radius);
        glow.addColorStop(0, "#effffb"); glow.addColorStop(0.35, color); glow.addColorStop(1, "#172a36");
        ctx.fillStyle = glow; ctx.beginPath(); ctx.arc(point.x, point.y, radius, 0, Math.PI * 2); ctx.fill();
        if (point.reference && point.base.position === selected) {
          ctx.strokeStyle = "#f2be68"; ctx.lineWidth = 2; ctx.beginPath(); ctx.arc(point.x, point.y, radius + 4, 0, Math.PI * 2); ctx.stroke();
        }
      }
      hitsRef.current = projected.map(p => ({ x: p.a.x, y: p.a.y, position: p.base.position }));
      ctx.fillStyle = "#b9c7da"; ctx.font = "12px system-ui";
      ctx.fillText("REFERENCE STRAND · 5′ → 3′", 18, 26);
      ctx.fillStyle = "#8397b7"; ctx.fillText("Schematic coordinates · not an atomic structure", 18, height - 18);
    };
    draw();
    const observer = new ResizeObserver(draw); observer.observe(canvas);
    return () => observer.disconnect();
  }, [bases, yaw, pitch, zoom, selected, phase]);

  if (!sequence) return <p className="rounded-lg border border-border p-5 text-sm text-muted">No source sequence is available for the CasAI scene. This view never substitutes a sample sequence.</p>;
  const selectedBase = bases.find(base => base.position === selected);
  const maxStart = Math.max(1, sequence.length - MAX_SCENE_BASES + 1);
  return <section className="overflow-hidden rounded-xl border border-border bg-bg-card" aria-label="CasAI interactive sequence scene">
    <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border p-4">
      <div><h2 className="font-serif-display text-xl">CasAI sequence explorer</h2><p className="mt-1 text-xs text-muted">Original 3D schematic · drag to orbit · select a base · scroll to zoom</p></div>
      <button type="button" className="rounded-lg border border-border-strong px-3 py-2 text-xs font-semibold" onClick={() => { setYaw(-0.3); setPitch(0.3); setZoom(1); setWindowStart(initialSceneStart(sequence.length, geometry?.protospacerStart)); setSelected(null); }}>Reset view</button>
    </div>
    {renderError ? <p role="alert" className="p-5 text-sm">Canvas rendering is unavailable. Sequence and result details remain available below.</p> : <canvas
      ref={canvasRef} className="h-[340px] w-full touch-none cursor-grab"
      tabIndex={0} role="img" aria-label={`Interactive 3D schematic of reference bases ${windowStart}–${Math.min(sequence.length, windowStart + MAX_SCENE_BASES - 1)}. Use arrow keys to orbit and plus or minus to zoom. Select a position with the Base position control below.`}
      onKeyDown={event => {
        if (["ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown", "+", "-", "="].includes(event.key)) event.preventDefault();
        if (event.key === "ArrowLeft") setYaw(v => v - 0.15);
        if (event.key === "ArrowRight") setYaw(v => v + 0.15);
        if (event.key === "ArrowUp") setPitch(v => Math.max(-1.3, v - 0.15));
        if (event.key === "ArrowDown") setPitch(v => Math.min(1.3, v + 0.15));
        if (["+", "="].includes(event.key)) setZoom(v => Math.min(2.5, v + 0.1));
        if (event.key === "-") setZoom(v => Math.max(0.5, v - 0.1));
      }}
      onWheel={event => setZoom(v => Math.max(0.5, Math.min(2.5, v - event.deltaY * 0.001)))}
      onPointerDown={event => { event.currentTarget.setPointerCapture(event.pointerId); dragRef.current = { x: event.clientX, y: event.clientY, distance: 0 }; }}
      onPointerMove={event => { const drag = dragRef.current; if (!drag) return; const dx = event.clientX - drag.x, dy = event.clientY - drag.y; drag.distance += Math.abs(dx) + Math.abs(dy); drag.x = event.clientX; drag.y = event.clientY; setYaw(v => v + dx * 0.008); setPitch(v => Math.max(-1.3, Math.min(1.3, v + dy * 0.008))); }}
      onPointerCancel={() => { dragRef.current = null; }}
      onPointerUp={event => {
        const drag = dragRef.current; dragRef.current = null;
        if (event.currentTarget.hasPointerCapture(event.pointerId)) event.currentTarget.releasePointerCapture(event.pointerId);
        if (!drag || drag.distance > 6) return;
        const rect = event.currentTarget.getBoundingClientRect();
        const hit = hitsRef.current.map(h => ({ ...h, distance: Math.hypot(h.x - event.clientX + rect.left, h.y - event.clientY + rect.top) })).sort((a, b) => a.distance - b.distance)[0];
        if (hit && hit.distance < 20) setSelected(hit.position);
      }}
    />}
    <div className="grid gap-4 p-4 sm:grid-cols-2">
      <label className="text-xs text-text-secondary">Sequence window: {windowStart}–{Math.min(sequence.length, windowStart + MAX_SCENE_BASES - 1)} of {sequence.length} bp
        <input aria-label="Sequence window start" type="range" min={1} max={maxStart} value={Math.min(windowStart, maxStart)} onChange={event => { setWindowStart(Number(event.target.value)); setSelected(null); }} className="mt-3 block w-full accent-accent" disabled={maxStart === 1} />
      </label>
      <label className="text-xs text-text-secondary">Base position
        <input type="number" min={1} max={sequence.length} value={selected ?? ""} placeholder="Select a position" className="mt-2 block w-full rounded border border-border bg-bg px-3 py-2 text-text" onChange={event => {
          const position = Number(event.target.value);
          if (!Number.isInteger(position) || position < 1 || position > sequence.length) { setSelected(null); return; }
          setSelected(position);
          if (!bases.some(base => base.position === position)) setWindowStart(Math.max(1, Math.min(position - 16, maxStart)));
        }} />
      </label>
    </div>
    <p aria-live="polite" className="border-t border-border px-4 py-3 text-sm text-text-secondary">{selectedBase ? `Position ${selectedBase.position}: reference ${selectedBase.reference}, complementary base ${complementBase(selectedBase.reference)}; computed output ${selectedBase.output ?? "unavailable"}${selectedBase.guide ? "; inside the recorded guide span" : ""}.` : "Select a base to inspect reference and computed output. Mint: reference strand · slate: complementary strand · amber: computed changes revealed in EDIT phase."}</p>
    <p className="px-4 pb-4 text-xs leading-5 text-muted">Geometry is illustrative. The sequence and available edit annotations come from this run; this scene does not calculate enzyme motion, binding energies or experimental editing outcomes.</p>
  </section>;
}
