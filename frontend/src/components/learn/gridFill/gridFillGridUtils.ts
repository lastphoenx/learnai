export const GRID_FILL_COLOR_MAP: Record<string, string> = {
  yellow: "#e6c200",
  green: "#2d9f4e",
  purple: "#8b4bb8",
  blue: "#3b82c4",
  orange: "#e07b2d",
  empty: "transparent",
};

export function emptyGrid(rows: number, cols: number): (string | number | null)[][] {
  return Array.from({ length: rows }, () => Array.from({ length: cols }, () => null));
}

export function resizeGrid(
  prev: (string | number | null)[][],
  rows: number,
  cols: number,
): (string | number | null)[][] {
  const next = emptyGrid(rows, cols);
  for (let ri = 0; ri < rows; ri++) {
    for (let ci = 0; ci < cols; ci++) {
      if (ri < prev.length && ci < (prev[ri]?.length ?? 0)) {
        next[ri][ci] = prev[ri][ci];
      }
    }
  }
  return next;
}
