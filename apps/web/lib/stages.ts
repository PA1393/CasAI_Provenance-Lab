export type Stage = { key: string; label: string };

export const STAGES: Stage[] = [
  { key: "input",    label: "Pre-flight checks" },
  { key: "fields",   label: "Field extraction" },
  { key: "extract",  label: "Intent and guide selection" },
  { key: "simulate", label: "Sequence computation" },
  { key: "score",    label: "Scoring" },
  { key: "results",  label: "Result recording" },
  { key: "summary",  label: "Summary generation" },
];
