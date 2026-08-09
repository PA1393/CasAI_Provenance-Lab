"use client";

import { useMemo } from "react";
import type { ProvenanceEvent } from "@/lib/api/client";

// The pipeline's fixed base-editing geometry (apps/api/app/modules/simulation).
const GUIDE_LEN = 20;
const PAM_LEN = 3;
const EDIT_WINDOW: [number, number] = [4, 8]; // 1-indexed protospacer positions

// Bases drawn at once. The track focuses on the edit site; the minimap below it
// shows where that window sits in the full sequence.
const VIEW_BASES = 64;

// The phase index at which the edit is applied, matching the PHASES timeline in
// run-simulation.tsx (SCAN, BIND, ACT, EDIT). Before this, the track shows the
// unedited sequence so the conversion is something you watch happen.
const EDIT_PHASE = 3;

// Hex literals rather than Tailwind classes because SVG fill/stroke need them.
// Values track the theme tokens in tailwind.config.ts; "edited" is the orange
// already used for edited output in run-simulation.tsx and molecule-3d.tsx.
const COLORS = {
  context: "#8a8a95", // muted — bases outside the guide
  guide: "#7dd3d8", // accent — protospacer
  pam: "#f5b942", // accent-amber
  edited: "#fb923c",
  border: "#1f1f28",
};

const CHAR_W = 13;
const PAD_X = 10;
const Y_RULER = 12;
const Y_REF = 44;
const Y_EDIT = 72;
const Y_FEATURE = 88;
const Y_MINIMAP = 112;
const SVG_H = 128;

/** Edit geometry as emitted by the pipeline's `simulation_executed` event. */
export type EditGeometry = {
  edited: boolean;
  strand: "+" | "-" | null;
  /** 1-indexed, sense orientation. */
  protospacerStart: number | null;
  /** 1-indexed bp, sense orientation. */
  editedPositions: number[];
  pamFound: string | null;
  reason: string | null;
};

/**
 * Pull the edit geometry out of a run's provenance trail.
 *
 * Mirrors the `extractRagSources` pattern in run-tabs.tsx: the pipeline records
 * everything the viewer needs in the event payload, so the UI reads the audit
 * trail rather than recomputing biology it has no business recomputing.
 * Returns null when the run never reached the simulate stage.
 */
export function extractEditGeometry(provenance: ProvenanceEvent[]): EditGeometry | null {
  const payload = provenance.find((e) => e.event_type === "simulation_executed")?.payload;
  if (!payload) return null;

  const strand = payload["strand"];
  const start = payload["protospacer_start"];
  const positions = payload["edited_positions"];
  const pam = payload["pam_found"];
  const reason = payload["reason"];

  return {
    edited: payload["edited"] === true,
    strand: strand === "+" || strand === "-" ? strand : null,
    protospacerStart: typeof start === "number" ? start : null,
    editedPositions: Array.isArray(positions)
      ? positions.filter((p): p is number => typeof p === "number")
      : [],
    pamFound: typeof pam === "string" ? pam : null,
    reason: typeof reason === "string" ? reason : null,
  };
}

/**
 * Map a 1-indexed protospacer position to a 0-indexed sense-strand coordinate.
 *
 * On the minus strand the protospacer runs antisense, so position 1 sits at the
 * *highest* sense coordinate of the span — the engine already maps its output
 * back to sense orientation, and this keeps the overlay consistent with it.
 */
function protoPosToSense0(pos: number, start0: number, strand: "+" | "-" | null): number {
  return strand === "-" ? start0 + GUIDE_LEN - pos : start0 + (pos - 1);
}

type Props = {
  /** Original sequence from the research object. */
  sequence?: string | null;
  /** Edited sequence from the run's result. */
  editedSequence?: string | null;
  geometry?: EditGeometry | null;
  /** Timeline phase from run-simulation; the edit reveals at EDIT_PHASE. */
  phase?: number;
};

export function SequenceTrack({ sequence, editedSequence, geometry, phase = EDIT_PHASE }: Props) {
  const view = useMemo(() => {
    if (!sequence) return null;

    const len = sequence.length;
    const start0 = geometry?.protospacerStart != null ? geometry.protospacerStart - 1 : null;
    const strand = geometry?.strand ?? null;

    // The PAM sits immediately 3' of the protospacer. In sense coordinates that
    // is just past the span on the plus strand, and just before it on the minus.
    let guide: { from: number; to: number } | null = null;
    let pam: { from: number; to: number } | null = null;
    let windowSpan: { from: number; to: number } | null = null;

    if (start0 != null && start0 >= 0) {
      guide = { from: start0, to: start0 + GUIDE_LEN - 1 };
      pam =
        strand === "-"
          ? { from: start0 - PAM_LEN, to: start0 - 1 }
          : { from: guide.to + 1, to: guide.to + PAM_LEN };
      const a = protoPosToSense0(EDIT_WINDOW[0], start0, strand);
      const b = protoPosToSense0(EDIT_WINDOW[1], start0, strand);
      windowSpan = { from: Math.min(a, b), to: Math.max(a, b) };
    }

    // Centre the viewport on the feature, else fall back to the sequence start.
    const focusFrom = guide && pam ? Math.min(guide.from, pam.from) : 0;
    const focusTo = guide && pam ? Math.max(guide.to, pam.to) : Math.min(len, VIEW_BASES) - 1;
    const centre = Math.floor((focusFrom + focusTo) / 2);
    const from = Math.max(0, Math.min(centre - Math.floor(VIEW_BASES / 2), len - VIEW_BASES));
    const to = Math.min(len, Math.max(0, from) + VIEW_BASES);

    return { from: Math.max(0, from), to, len, guide, pam, windowSpan };
  }, [sequence, geometry]);

  if (!sequence || !view) {
    return (
      <p className="font-mono text-xs text-muted">
        No sequence stored on this research object — upload a FASTA to see the edit rendered
        against real bases.
      </p>
    );
  }

  const { from, to, len, guide, pam, windowSpan } = view;
  const editedSet = new Set(geometry?.editedPositions.map((p) => p - 1) ?? []);
  const revealed = phase >= EDIT_PHASE;
  // Only trust the edited sequence when it lines up with the original; a length
  // mismatch means we would be comparing different coordinate spaces.
  const edited = editedSequence?.length === len ? editedSequence : null;

  const count = to - from;
  const svgW = PAD_X * 2 + count * CHAR_W;
  const xOf = (i: number) => PAD_X + (i - from) * CHAR_W;
  const spanRect = (s: { from: number; to: number }) => {
    const lo = Math.max(s.from, from);
    const hi = Math.min(s.to, to - 1);
    return hi < lo ? null : { x: xOf(lo), w: (hi - lo + 1) * CHAR_W };
  };

  const guideRect = guide && spanRect(guide);
  const pamRect = pam && spanRect(pam);
  const windowRect = windowSpan && spanRect(windowSpan);

  // Ruler ticks every 10 bases, on absolute 1-indexed coordinates.
  const ticks: number[] = [];
  for (let i = from; i < to; i++) {
    if ((i + 1) % 10 === 0) ticks.push(i);
  }

  return (
    <div className="flex flex-col gap-3">
      <svg
        viewBox={`0 0 ${svgW} ${SVG_H}`}
        className="h-auto w-full"
        role="img"
        aria-label={`Sequence ${from + 1} to ${to} with the edit site annotated`}
      >
        {/* edit window shading, drawn first so bases sit on top */}
        {windowRect && (
          <rect
            x={windowRect.x}
            y={Y_REF - 16}
            width={windowRect.w}
            height={Y_EDIT - Y_REF + 22}
            fill={COLORS.guide}
            opacity={0.09}
            rx={2}
          />
        )}

        {/* coordinate ruler */}
        {ticks.map((i) => (
          <g key={`tick-${i}`}>
            <text
              x={xOf(i) + CHAR_W / 2}
              y={Y_RULER}
              fill={COLORS.context}
              fontSize={9}
              fontFamily="monospace"
              textAnchor="middle"
            >
              {i + 1}
            </text>
            <line
              x1={xOf(i) + CHAR_W / 2}
              y1={Y_RULER + 4}
              x2={xOf(i) + CHAR_W / 2}
              y2={Y_RULER + 9}
              stroke={COLORS.border}
              strokeWidth={1}
            />
          </g>
        ))}

        {/* row labels */}
        <text x={0} y={Y_REF - 20} fill={COLORS.context} fontSize={8} fontFamily="monospace">
          REF
        </text>
        <text x={0} y={Y_EDIT - 20} fill={COLORS.context} fontSize={8} fontFamily="monospace">
          EDIT
        </text>

        {Array.from({ length: count }, (_, k) => {
          const i = from + k;
          const inGuide = guide != null && i >= guide.from && i <= guide.to;
          const inPam = pam != null && i >= pam.from && i <= pam.to;
          const changed = editedSet.has(i);
          const x = xOf(i) + CHAR_W / 2;

          const refColor = inPam ? COLORS.pam : inGuide ? COLORS.guide : COLORS.context;
          const editChar = revealed && edited ? edited[i] : sequence[i];
          const showChanged = changed && revealed;

          return (
            <g key={i}>
              <text
                x={x}
                y={Y_REF}
                fill={refColor}
                fontSize={13}
                fontFamily="monospace"
                textAnchor="middle"
              >
                {sequence[i]}
              </text>

              {showChanged && (
                <rect
                  x={xOf(i) + 1}
                  y={Y_EDIT - 13}
                  width={CHAR_W - 2}
                  height={17}
                  fill={COLORS.edited}
                  opacity={0.18}
                  rx={2}
                />
              )}
              <text
                x={x}
                y={Y_EDIT}
                fill={showChanged ? COLORS.edited : refColor}
                fontSize={13}
                fontWeight={showChanged ? 700 : 400}
                fontFamily="monospace"
                textAnchor="middle"
              >
                {editChar}
              </text>
            </g>
          );
        })}

        {/* feature bar: protospacer span and PAM */}
        {guideRect && (
          <>
            <rect
              x={guideRect.x}
              y={Y_FEATURE}
              width={guideRect.w}
              height={5}
              fill={COLORS.guide}
              opacity={0.75}
              rx={2}
            />
            <text
              x={guideRect.x + guideRect.w / 2}
              y={Y_FEATURE + 16}
              fill={COLORS.guide}
              fontSize={8}
              fontFamily="monospace"
              textAnchor="middle"
            >
              {`PROTOSPACER ${GUIDE_LEN}nt ${geometry?.strand ?? "+"}`}
            </text>
          </>
        )}
        {pamRect && (
          <>
            <rect
              x={pamRect.x}
              y={Y_FEATURE}
              width={pamRect.w}
              height={5}
              fill={COLORS.pam}
              opacity={0.85}
              rx={2}
            />
            <text
              x={pamRect.x + pamRect.w / 2}
              y={Y_FEATURE + 16}
              fill={COLORS.pam}
              fontSize={8}
              fontFamily="monospace"
              textAnchor="middle"
            >
              PAM
            </text>
          </>
        )}

        {/* minimap: where this window sits in the whole sequence */}
        <rect
          x={PAD_X}
          y={Y_MINIMAP}
          width={svgW - PAD_X * 2}
          height={4}
          fill={COLORS.border}
          rx={2}
        />
        <rect
          x={PAD_X + ((svgW - PAD_X * 2) * from) / len}
          y={Y_MINIMAP - 1}
          width={Math.max(2, ((svgW - PAD_X * 2) * count) / len)}
          height={6}
          fill={COLORS.guide}
          rx={2}
        />
      </svg>

      <div className="flex flex-wrap items-center gap-x-4 gap-y-1 font-mono text-[10px] text-muted">
        <Legend color={COLORS.guide} label="Protospacer" />
        <Legend color={COLORS.pam} label={geometry?.pamFound ? `PAM ${geometry.pamFound}` : "PAM"} />
        <Legend color={COLORS.edited} label="Edited base" />
        <span className="ml-auto">
          {`${from + 1}–${to} of ${len} bp`}
          {geometry?.editedPositions.length
            ? ` · edit at ${geometry.editedPositions.join(", ")}`
            : ""}
        </span>
      </div>

      {geometry && !geometry.edited && geometry.reason && (
        <p className="font-mono text-[10px] text-muted">
          No base converted — {geometry.reason}.
        </p>
      )}
    </div>
  );
}

function Legend({ color, label }: { color: string; label: string }) {
  return (
    <span className="flex items-center gap-1.5">
      <span className="inline-block h-2 w-2 rounded-sm" style={{ backgroundColor: color }} />
      {label}
    </span>
  );
}
