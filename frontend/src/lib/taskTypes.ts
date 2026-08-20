export type UnitTaskType = {
  key: string;
  label: string;
  description: string;
  hint: string;
};

export type MathFocusOption = {
  key: string;
  label: string;
};

const FALLBACK_TASK_TYPES: UnitTaskType[] = [
  {
    key: "mixed",
    label: "Gemischt (Lerntext + Quiz)",
    description: "Standard für neue Themen: kurze Erklärung pro Block, danach Verständnisfragen.",
    hint: "",
  },
  {
    key: "explain",
    label: "Erklären / Lerntext",
    description: "Wenig Quiz, dafür ausführliche Erklärung.",
    hint: "",
  },
  {
    key: "quiz",
    label: "Quiz / Verständnisfragen",
    description: "Kurze Einleitung, dann viele Fragen.",
    hint: "",
  },
  {
    key: "practice",
    label: "Übungen",
    description: "Aufgaben zum Selberlösen mit Lösungshinweisen.",
    hint: "",
  },
  {
    key: "math",
    label: "Rechnen (Mathematik)",
    description: "Rechenaufgaben mit Lösungsweg — Mathe-Schwerpunkt wählen.",
    hint: "",
  },
  {
    key: "workbook",
    label: "Am Heft / Arbeitsblatt",
    description: "Eng am hochgeladenen Schulmaterial orientiert.",
    hint: "",
  },
  {
    key: "review",
    label: "Wiederholung / Festigung",
    description: "Wiederholung zu bestehendem Stoff, weniger Erklärung.",
    hint: "",
  },
  {
    key: "exam",
    label: "Kurzprüfung",
    description: "Nur Aufgaben, keine Hilfen.",
    hint: "",
  },
  {
    key: "vocab",
    label: "Vokabeln / Sprache",
    description: "Fremdsprachen: Wort, Bedeutung, Beispielsatz.",
    hint: "",
  },
  {
    key: "interactive",
    label: "Interaktiver Lerntrainer",
    description: "Viele Lernkarten, Quiz-Challenge, Wissens-Hub — spielerisch.",
    hint: "",
  },
];

const FALLBACK_MATH_FOCUS: MathFocusOption[] = [
  { key: "", label: "— Mathe-Schwerpunkt (optional) —" },
  { key: "fractions", label: "Bruchrechnen" },
  { key: "decimals", label: "Dezimalzahlen & Komma" },
  { key: "place_value", label: "Stellenwert / Zahlenräume" },
  { key: "add_sub", label: "Addition & Subtraktion" },
  { key: "mul_div", label: "Multiplikation & Division" },
  { key: "geometry", label: "Geometrie" },
  { key: "measures", label: "Größen & Einheiten" },
  { key: "patterns", label: "Reihen & Muster" },
  { key: "percent_ratio", label: "Prozent & Dreisatz" },
  { key: "negative", label: "Negative Zahlen" },
  { key: "other", label: "Sonstiges" },
];

export function showMathFocus(taskType: string, subject: string) {
  if (["math", "workbook", "practice"].includes(taskType)) return true;
  return /mathe|math|rechnen/i.test(subject);
}

export function taskTypeLabel(key: string, types?: UnitTaskType[]) {
  const list = types?.length ? types : FALLBACK_TASK_TYPES;
  return list.find((t) => t.key === key)?.label ?? key;
}

export function mathFocusLabel(key: string | null | undefined, options = FALLBACK_MATH_FOCUS) {
  if (!key) return null;
  return options.find((o) => o.key === key)?.label ?? key;
}

const LANG_LABELS: Record<string, string> = {
  de: "Deutsch",
  fr: "Französisch",
  it: "Italienisch",
  en: "Englisch",
};

export function languageLabel(code: string) {
  return LANG_LABELS[code] ?? code;
}

export { FALLBACK_TASK_TYPES, FALLBACK_MATH_FOCUS };
