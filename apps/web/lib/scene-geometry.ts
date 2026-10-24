export type SceneBase = { position: number; reference: string; output: string | null; changed: boolean; guide: boolean; x: number; y: number; z: number };
export const MAX_SCENE_BASES = 64;

// Original CasAI display geometry, NOT measured molecular coordinates.
// All positions remain 1-based coordinates of the supplied reference strand.
export function sequenceScene(sequence: string, edited: string | null | undefined, start: number, guideStart?: number | null): SceneBase[] {
  const from = Math.max(0, Math.min(Math.floor(Number.isFinite(start) ? start : 1) - 1, Math.max(0, sequence.length - 1)));
  const count = Math.min(MAX_SCENE_BASES, sequence.length - from);
  const matched = edited?.length === sequence.length ? edited : null;
  const validGuide = typeof guideStart === "number" && Number.isInteger(guideStart) && guideStart >= 1 && guideStart + 19 <= sequence.length;
  return Array.from({ length: count }, (_, i) => {
    const position = from + i + 1;
    const reference = sequence[position - 1].toUpperCase();
    const output = matched ? matched[position - 1].toUpperCase() : null;
    const angle = (position - 1) * Math.PI * 2 / 10.5;
    return { position, reference, output, changed: output !== null && output !== reference,
      guide: !!validGuide && position >= guideStart! && position < guideStart! + 20,
      x: (i - (count - 1) / 2) * 0.32, y: Math.cos(angle) * 1.6, z: Math.sin(angle) * 1.6 };
  });
}

export function initialSceneStart(length: number, guideStart?: number | null): number {
  const focus = typeof guideStart === "number" && Number.isInteger(guideStart) && guideStart >= 1 && guideStart <= length ? guideStart : 1;
  return Math.max(1, Math.min(focus - 16, Math.max(1, length - MAX_SCENE_BASES + 1)));
}

export function complementBase(base: string): string {
  return ({ A: "T", T: "A", U: "A", C: "G", G: "C" } as Record<string, string>)[base] ?? "N";
}
