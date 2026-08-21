export type UnitTaskType = {
  key: string;
  label: string;
  select_label?: string;
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
    label: "Gemischt",
    select_label: "Gemischt (Lerntext lesen → Quiz, Block für Block)",
    description: "Standard für neue Themen: kurze Erklärung pro Block, danach Verständnisfragen.",
    hint: "",
  },
  {
    key: "explain",
    label: "Erklären",
    select_label: "Erklären (ausführlicher Text, kaum Quiz)",
    description: "Wenig Quiz, dafür ausführliche Erklärung.",
    hint: "",
  },
  {
    key: "quiz",
    label: "Quiz",
    select_label: "Quiz (kurzer Text, viele Verständnisfragen)",
    description: "Kurze Einleitung, dann viele Fragen.",
    hint: "",
  },
  {
    key: "practice",
    label: "Übungen",
    select_label: "Übungen (selbst lösen, mit Lösungshinweis)",
    description: "Aufgaben zum Selberlösen mit Lösungshinweisen.",
    hint: "",
  },
  {
    key: "math",
    label: "Rechnen",
    select_label: "Rechnen (Mathe-Aufgaben mit Lösungsweg)",
    description: "Rechenaufgaben mit Lösungsweg — Mathe-Schwerpunkt wählen.",
    hint: "",
  },
  {
    key: "workbook",
    label: "Am Heft",
    select_label: "Am Heft (nah am Arbeitsblatt, gleiche Aufgabenarten)",
    description: "Eng am hochgeladenen Schulmaterial orientiert.",
    hint: "",
  },
  {
    key: "review",
    label: "Wiederholung",
    select_label: "Wiederholung (bekannter Stoff, ähnliche Aufgaben)",
    description: "Wiederholung zu bestehendem Stoff, weniger Erklärung.",
    hint: "",
  },
  {
    key: "exam",
    label: "Kurzprüfung",
    select_label: "Kurzprüfung (nur Aufgaben, keine Hilfen)",
    description: "Nur Aufgaben, keine Hilfen.",
    hint: "",
  },
  {
    key: "vocab",
    label: "Vokabeln",
    select_label: "Vokabeln (Fremdsprache: Wort, Bedeutung, Beispiel)",
    description: "Fremdsprachen: Wort, Bedeutung, Beispielsatz.",
    hint: "",
  },
  {
    key: "interactive",
    label: "Lerntrainer",
    select_label: "Lerntrainer (Karten, Check, Eingabe-Übungen, Wissens-Hub)",
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

export function taskTypeSelectLabel(key: string, types?: UnitTaskType[]) {
  const list = types?.length ? types : FALLBACK_TASK_TYPES;
  const item = list.find((t) => t.key === key);
  return item?.select_label ?? item?.label ?? key;
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
