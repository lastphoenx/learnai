import type { HeightMatrix } from "@/lib/isoBuilding";

/** Spiegelt building_projections() im Backend (Zeile 0 = oberste Würfelreihe). */
export function buildingProjections(matrix: HeightMatrix): {
  top: number[][];
  front: number[][];
  right: number[][];
} {
  const rows = matrix.length;
  const cols = matrix[0]?.length ?? 0;
  const maxH = Math.max(...matrix.flat(), 1);

  const top: number[][] = matrix.map((row) => [...row]);

  const front: number[][] = Array.from({ length: maxH }, () => Array.from({ length: cols }, () => 0));
  for (let x = 0; x < cols; x++) {
    let colMax = 0;
    for (let y = 0; y < rows; y++) {
      colMax = Math.max(colMax, matrix[y]?.[x] ?? 0);
    }
    for (let zi = 0; zi < maxH; zi++) {
      const row = maxH - 1 - zi;
      front[row][x] = zi < colMax ? 1 : 0;
    }
  }

  const right: number[][] = Array.from({ length: maxH }, () => Array.from({ length: rows }, () => 0));
  for (let y = 0; y < rows; y++) {
    let rowMax = 0;
    for (let x = 0; x < cols; x++) {
      rowMax = Math.max(rowMax, matrix[y]?.[x] ?? 0);
    }
    for (let zi = 0; zi < maxH; zi++) {
      const row = maxH - 1 - zi;
      right[row][y] = zi < rowMax ? 1 : 0;
    }
  }

  return { top, front, right };
}
