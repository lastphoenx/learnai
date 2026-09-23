import type { HeightMatrix } from "@/lib/isoBuilding";

export type ViewpointCandidateLike = {
  id: string;
  label?: string;
  x?: number;
  y?: number;
};

const FALLBACK_XY: Record<string, [number, number]> = {
  A: [0.5, 0.9],
  B: [0.88, 0.5],
  C: [0.5, 0.1],
  D: [0.12, 0.5],
};

/** Normierte Plan-Koordinaten (0–1), y=0.9 ≈ vorne (unten im Grundriss). */
export function resolveViewpointNorm(c: ViewpointCandidateLike): [number, number] {
  if (typeof c.x === "number" && typeof c.y === "number") {
    return [c.x, c.y];
  }
  return FALLBACK_XY[c.id] ?? [0.5, 0.5];
}

const GAP = 1.02;

/** Position in der gleichen lokalen Gruppe wie VoxelBuilding (vor offsetX/offsetZ). */
export function planNormToLocalPosition(
  nx: number,
  ny: number,
  cols: number,
  rows: number,
): [number, number, number] {
  const w = Math.max(0, (cols - 1) * GAP);
  const d = Math.max(0, (rows - 1) * GAP);
  const cx = w / 2;
  const cz = d / 2;
  const dx = nx - 0.5;
  const dy = ny - 0.5;
  const len = Math.hypot(dx, dy) || 1;
  const dist = Math.max(w, d, GAP) * 0.55 + 1.4;
  return [cx + (dx / len) * dist, 0.22, cz + (dy / len) * dist];
}

export function buildingGroupOffset(matrix: HeightMatrix): [number, number, number] {
  const cols = matrix[0]?.length ?? 1;
  const rows = matrix.length;
  const offsetX = -((cols - 1) * GAP) / 2;
  const offsetZ = -((rows - 1) * GAP) / 2;
  return [offsetX, 0, offsetZ];
}
