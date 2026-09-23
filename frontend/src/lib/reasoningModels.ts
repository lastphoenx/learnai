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

/** Anzeige für Einheiten-KI-Panel (effort null/default = API-Standard). */
export function formatReasoningEffort(model: string, effort?: string | null): string | null {
  if (!isReasoningModel(model)) return null;
  const raw = (effort || "").trim().toLowerCase();
  if (!raw || raw === "default") {
    return REASONING_EFFORT_OPTIONS[0].label;
  }
  const opt = REASONING_EFFORT_OPTIONS.find((o) => o.value === raw);
  return opt?.label ?? raw;
}
