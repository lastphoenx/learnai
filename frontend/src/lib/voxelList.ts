import type { HeightMatrix } from "@/lib/isoBuilding";

export type VoxelCoord = { gx: number; gy: number; gz: number };

function heightAt(matrix: HeightMatrix, x: number, y: number): number {
  if (y < 0 || y >= matrix.length || x < 0 || x >= matrix[0].length) return 0;
  return matrix[y][x] ?? 0;
}

/** Alle Würfel mit Höhe > 0 — ohne Iso-Face-Culling (OrbitControls). */
export function listVoxelsFromHeightMatrix(matrix: HeightMatrix): VoxelCoord[] {
  const out: VoxelCoord[] = [];
  const rows = matrix.length;
  const cols = matrix[0]?.length ?? 0;
  for (let gy = 0; gy < rows; gy++) {
    for (let gx = 0; gx < cols; gx++) {
      const h = heightAt(matrix, gx, gy);
      for (let gz = 0; gz < h; gz++) {
        out.push({ gx, gy, gz });
      }
    }
  }
  return out;
}
