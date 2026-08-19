/** Fehler-Tags für Prüfungsanalyse (Labels wie im Backend). */

export const EXAM_ERROR_TAG_LABELS: Record<string, string> = {
  fractions_denominator: "Brüche: Nenner verwechselt",
  fractions_numerator: "Brüche: Zähler verwechselt",
  fractions_simplify: "Brüche: Kürzen/Erweitern",
  fractions_compare: "Brüche: Vergleichen/Ordnen",
  fractions_add_sub: "Brüche: Addieren/Subtrahieren",
  fractions_mul_div: "Brüche: Multiplizieren/Dividieren",
  decimals_place: "Dezimalzahlen: Stellenwert",
  decimals_round: "Dezimalzahlen: Runden",
  place_value: "Stellenwert verwechselt",
  unit_conversion: "Einheiten-Umrechnung",
  measures_length: "Längenangaben",
  measures_mass: "Massenangaben",
  measures_volume: "Volumenangaben",
  measures_area: "Flächenangaben",
  measures_time: "Zeitangaben",
  addition_carry: "Addition: Übertrag",
  subtraction_borrow: "Subtraktion: Entlehnen",
  multiplication_table: "Einmaleins / Malreihen",
  division_remainder: "Division: Rest",
  geometry_area: "Geometrie: Fläche",
  geometry_perimeter: "Geometrie: Umfang",
  geometry_angle: "Geometrie: Winkel",
  percent_calc: "Prozentrechnung",
  ratio_proportion: "Verhältnis / Dreisatz",
  negative_sign: "Negative Zahlen: Vorzeichen",
  order_of_operations: "Rechenreihenfolge",
  reading_comprehension: "Textverständnis",
  spelling: "Rechtschreibung",
  grammar: "Grammatik",
  vocabulary: "Wortschatz",
  careless_error: "Flüchtigkeitsfehler",
  method_missing: "Lösungsweg fehlt",
  calculation_error: "Rechenfehler",
};

export function labelForErrorTag(tag: string): string {
  const key = tag.trim().toLowerCase();
  return EXAM_ERROR_TAG_LABELS[key] || key.replace(/_/g, " ");
}

export const EXAM_ERROR_TAG_OPTIONS = Object.entries(EXAM_ERROR_TAG_LABELS).map(([value, label]) => ({
  value,
  label,
}));
