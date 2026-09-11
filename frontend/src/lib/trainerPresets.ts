import type { TrainerOptions } from "@/lib/api";

export type TrainerPresetId = "posten_compact" | "standard" | "exam_review" | "custom";

export type TrainerPresetDefinition = {
  id: TrainerPresetId;
  label: string;
  hint: string;
  options: TrainerOptions | null;
  limits?: { cards_min: number; cards_max: number; questions_min: number; questions_max: number };
};

export const FALLBACK_TRAINER_PRESETS: TrainerPresetDefinition[] = [
  {
    id: "posten_compact",
    label: "Posten kompakt (~10–15 Min)",
    hint: "Eine Doppelseite oder ein Heft-Posten — fokussiert, nicht überladen.",
    options: { cards: 12, questions: 8, style: "exam", answer_length: "short" },
  },
  {
    id: "standard",
    label: "Standard (tiefes Üben)",
    hint: "Viele Karten und Quizfragen (z. B. Mathe).",
    options: { cards: 50, questions: 50, style: "playful", answer_length: "short" },
  },
  {
    id: "exam_review",
    label: "Prüfung / Review",
    hint: "Quer-Wiederholung vor einer Lernzielkontrolle.",
    options: { cards: 15, questions: 28, style: "exam", answer_length: "short" },
  },
  {
    id: "custom",
    label: "Frei",
    hint: "Karten- und Quiz-Anzahl selbst wählen.",
    options: null,
    limits: { cards_min: 5, cards_max: 100, questions_min: 5, questions_max: 100 },
  },
];

export const TRAINER_CUSTOM_LIMITS = FALLBACK_TRAINER_PRESETS.find((p) => p.id === "custom")!.limits!;

export function presetById(
  presets: TrainerPresetDefinition[],
  id: TrainerPresetId,
): TrainerPresetDefinition {
  return presets.find((p) => p.id === id) ?? FALLBACK_TRAINER_PRESETS[1];
}

export function detectTrainerPresetId(
  presets: TrainerPresetDefinition[],
  options: TrainerOptions | undefined,
  stored?: string | null,
): TrainerPresetId {
  if (stored && presets.some((p) => p.id === stored)) {
    return stored as TrainerPresetId;
  }
  if (!options) return "standard";
  for (const preset of presets) {
    if (!preset.options) continue;
    const o = preset.options;
    if (
      o.cards === options.cards &&
      o.questions === options.questions &&
      o.style === options.style &&
      (o.answer_length || "short") === (options.answer_length || "short")
    ) {
      return preset.id;
    }
  }
  return "custom";
}

export function optionsForPreset(
  presets: TrainerPresetDefinition[],
  id: TrainerPresetId,
  current?: TrainerOptions,
): TrainerOptions {
  if (id === "custom" && current) {
    return current;
  }
  const preset = presetById(presets, id);
  if (preset.options) {
    return { ...preset.options, llm_provider: current?.llm_provider ?? null };
  }
  return current ?? { cards: 50, questions: 50, style: "playful", answer_length: "short" };
}
