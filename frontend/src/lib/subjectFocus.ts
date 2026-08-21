export type FocusOption = { key: string; label: string };

export type FocusGroup = {
  id: string;
  label: string;
  options: FocusOption[];
};

export const FALLBACK_FOCUS_GROUPS: FocusGroup[] = [
  {
    id: "math",
    label: "Mathematik",
    options: [
      { key: "fractions", label: "Bruchrechnen" },
      { key: "decimals", label: "Dezimalzahlen & Komma" },
      { key: "place_value", label: "Stellenwert / Zahlenräume" },
      { key: "add_sub", label: "Addition & Subtraktion" },
      { key: "mul_div", label: "Multiplikation & Division" },
      { key: "geometry", label: "Geometrie" },
      { key: "measures", label: "Größen & Einheiten" },
      { key: "patterns", label: "Reihen, Muster & Folgen" },
      { key: "percent_ratio", label: "Prozent, Verhältnis & Dreisatz" },
      { key: "negative", label: "Negative Zahlen" },
      { key: "other", label: "Sonstiges Mathe" },
    ],
  },
  {
    id: "language",
    label: "Sprachen",
    options: [
      { key: "lang_vocab", label: "Vokabular / Wortschatz" },
      { key: "lang_verbs", label: "Verben (Konjugation, unregelmässig)" },
      { key: "lang_nouns_adj", label: "Nomen, Artikel, Adjektive" },
      { key: "lang_pronouns", label: "Pronomen" },
      { key: "lang_tenses_pres", label: "Zeitformen: Präsens / Gegenwart" },
      { key: "lang_tenses_past", label: "Zeitformen: Präteritum / Imparfait" },
      { key: "lang_tenses_perf", label: "Zeitformen: Perfekt / Passé composé" },
      { key: "lang_tenses_pqp", label: "Zeitformen: Plusquamperfekt" },
      { key: "lang_conditional", label: "Konditional / Futur" },
      { key: "lang_grammar", label: "Grammatik allgemein" },
      { key: "lang_reading", label: "Leseverständnis" },
      { key: "lang_writing", label: "Schreiben / Ausdruck" },
    ],
  },
  {
    id: "mgu",
    label: "Mensch, Gesellschaft & Umwelt",
    options: [
      { key: "mgu_health", label: "Gesundheit & Körper" },
      { key: "mgu_nutrition", label: "Ernährung" },
      { key: "mgu_family", label: "Familie & Beziehungen" },
      { key: "mgu_economy", label: "Wirtschaft & Konsum" },
      { key: "mgu_civics", label: "Politik & Demokratie" },
      { key: "mgu_history", label: "Geschichte" },
      { key: "mgu_geography", label: "Geografie (CH, Europa, Welt)" },
      { key: "mgu_environment", label: "Umwelt & Nachhaltigkeit" },
      { key: "mgu_media", label: "Medien & Information" },
      { key: "mgu_culture", label: "Kultur & Religion" },
    ],
  },
  {
    id: "german",
    label: "Deutsch",
    options: [
      { key: "de_spelling", label: "Rechtschreibung" },
      { key: "de_grammar", label: "Grammatik" },
      { key: "de_reading", label: "Lesen & Textverständnis" },
      { key: "de_writing", label: "Schreiben & Aufsatz" },
      { key: "de_vocab", label: "Wortschatz" },
      { key: "de_lit", label: "Literatur" },
    ],
  },
  {
    id: "nature",
    label: "Natur & Technik",
    options: [
      { key: "nt_biology", label: "Biologie" },
      { key: "nt_physics", label: "Physik" },
      { key: "nt_chemistry", label: "Chemie" },
      { key: "nt_technology", label: "Technik" },
    ],
  },
];

export function detectFocusGroup(subject: string, taskType: string): string | null {
  if (taskType === "vocab") return "language";
  if (taskType === "math") return "math";
  const text = subject.toLowerCase();
  if (!text.trim()) return null;
  if (/mathe|math|rechnen|arith/.test(text)) return "math";
  if (/franz|engl|ital|fremdsprach|sprach|langue|english|french|vocab/.test(text)) return "language";
  if (/deutsch(?!\s*als\s*fremd)/.test(text) || text.trim() === "de") return "german";
  if (/mensch|gesellschaft|umwelt|\bmgu\b|räume.*zeit|rzg/.test(text)) return "mgu";
  if (/natur.*technik|\bn&t\b|biologie|physik|chemie/.test(text)) return "nature";
  return null;
}

export function showSubjectFocus(taskType: string, subject: string): boolean {
  if (["math", "vocab", "workbook", "practice", "interactive"].includes(taskType)) return true;
  return detectFocusGroup(subject, taskType) !== null;
}

export function focusOptionsForGroup(
  groupId: string | null,
  groups: FocusGroup[] = FALLBACK_FOCUS_GROUPS,
): FocusOption[] {
  if (!groupId) return [];
  return groups.find((g) => g.id === groupId)?.options ?? [];
}

export function focusLabel(
  key: string | null | undefined,
  groups: FocusGroup[] = FALLBACK_FOCUS_GROUPS,
): string | null {
  if (!key) return null;
  for (const group of groups) {
    const hit = group.options.find((o) => o.key === key);
    if (hit) return hit.label;
  }
  return key;
}

export function focusGroupLabel(
  groupId: string | null,
  groups: FocusGroup[] = FALLBACK_FOCUS_GROUPS,
): string | null {
  if (!groupId) return null;
  return groups.find((g) => g.id === groupId)?.label ?? null;
}
