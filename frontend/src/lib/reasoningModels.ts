/** OpenAI GPT-5 / o-Serie — reasoning_effort unterstützt. */
export function isReasoningModel(model: string): boolean {
  const m = (model || "").trim().toLowerCase();
  return /^(o\d|gpt-5)/.test(m);
}

export const REASONING_EFFORT_OPTIONS = [
  { value: "", label: "API-Standard" },
  { value: "low", label: "Niedrig" },
  { value: "medium", label: "Mittel" },
  { value: "high", label: "Hoch" },
] as const;
