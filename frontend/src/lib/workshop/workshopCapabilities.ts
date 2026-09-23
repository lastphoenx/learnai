/** Generisches Freischalt-Muster für RaumWerkstatt-Übungen (Kapazität / Phase / Hinweise). */

export function unlockedHintIds(hints: string[], unlockedCount: number): string[] {
  return hints.slice(0, Math.max(0, unlockedCount));
}

export type WorkshopModelUnlockResult<TMode extends string> = {
  unlockedModes: TMode[];
  showColumnInspector: boolean;
  solutionOverlayAllowed: boolean;
};

export function clampWorkshopMode<TMode extends string>(
  mode: TMode,
  unlockedModes: TMode[],
  fallback: TMode,
): TMode {
  if (unlockedModes.includes(mode)) return mode;
  return unlockedModes[0] ?? fallback;
}
