export type RunMode = "demo_cbe" | "demo_abe" | "assisted";
// Transparent rule-based restatement, not a scientific prediction or LLM answer.
export function clarifyPrompt(prompt: string, mode: RunMode) {
  const text = prompt.trim();
  if (!text) return null;
  const cbe = /\bcbe\b|cytosine|c\s*(?:→|->|to)\s*t/i.test(text);
  const abe = /\babe\b|adenine|a\s*(?:→|->|to)\s*g/i.test(text);
  const inferred = abe && !cbe ? "demo_abe" : cbe && !abe ? "demo_cbe" : null;
  return {
    inferred,
    conflict: inferred !== null && mode !== "assisted" && inferred !== mode,
    message: mode === "assisted"
      ? `Got it. Your stated objective is: “${text}”. You want the AI-assisted service to interpret it. The interpretation may be unavailable or unsuitable; it is not a validated biological prediction.`
      : `Got it. You want a rule-based ${mode === "demo_cbe" ? "C → T (CBE)" : "A → G (ABE)"} demonstration using the first compatible NGG site in the full saved sequence. Your text is the run label, not an instruction to change the gene's function.`,
    requiresChoice: cbe && abe,
  };
}
