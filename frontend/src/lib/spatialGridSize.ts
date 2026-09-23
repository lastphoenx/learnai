export type GridSizeHint = "given" | "derive";

export type ViewSize = { rows: number; cols: number };

export const PROJECTION_MAX_ROWS = 12;
export const PROJECTION_MAX_COLS = 8;

export function emptyNumberGrid(rows: number, cols: number): number[][] {
  const r = Math.max(1, Math.min(PROJECTION_MAX_ROWS, rows));
  const c = Math.max(1, Math.min(PROJECTION_MAX_COLS, cols));
  return Array.from({ length: r }, () => Array.from({ length: c }, () => 0));
}

export function normalizeGridSizeHint(raw: string | undefined | null): GridSizeHint {
  return raw === "derive" ? "derive" : "given";
}

/** derive: 1×1 start (Schüler wählt Grösse); given: vorgegebene rows/cols aus der Aufgabe. */
export function initialGridFillDimensions(rows: number, cols: number, gridSizeHint?: string | null): ViewSize {
  if (normalizeGridSizeHint(gridSizeHint) === "derive") {
    return { rows: 1, cols: 1 };
  }
  return { rows, cols };
}
