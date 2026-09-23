/** Didaktik: Faltvorschau nicht während der freien Eingabe (Lösung verrät Flächen-Zuordnung). */

export type NetValidatePhase = "inspect" | "decide";

export function netFoldHintAllowed(params: {
  validateMode: boolean;
  validatePhase: NetValidatePhase;
  selectedCount: number;
}): boolean {
  if (params.validateMode) {
    return params.validatePhase === "decide";
  }
  return params.selectedCount === 6;
}
