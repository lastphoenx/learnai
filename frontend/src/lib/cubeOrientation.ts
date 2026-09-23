/**
 * Gebäude-Festkoordinaten (unabhängig von Kameradrehung).
 * Geteilt von Kap. 1 (sichtbare Fläche/Farbe) und Kap. 5 (freies Drehen + Malen).
 */

import type { HeightMatrix } from "@/lib/isoBuilding";
import { faceId } from "@/lib/isoBuilding";

export type BuildingFace = "top" | "bottom" | "left" | "right" | "front" | "back";

export const BUILDING_FACE_NAMES: BuildingFace[] = [
  "top",
  "bottom",
  "left",
  "right",
  "front",
  "back",
];

/** Three.js BoxGeometry-Materialindex → Gebäudefläche (VoxelBuilding). */
export const BOX_MATERIAL_INDEX_TO_FACE: Record<number, BuildingFace> = {
  0: "right",
  1: "left",
  2: "top",
  3: "bottom",
  4: "front",
  5: "back",
};

export const BUILDING_FACE_TO_MATERIAL: Record<BuildingFace, number> = {
  right: 0,
  left: 1,
  top: 2,
  bottom: 3,
  front: 4,
  back: 5,
};

function heightAt(matrix: HeightMatrix, x: number, y: number): number {
  if (y < 0 || y >= matrix.length || x < 0 || x >= (matrix[0]?.length ?? 0)) return 0;
  return matrix[y][x] ?? 0;
}

/** Äussere Fläche am Voxel (6-Flächen-Modell; iso nutzt nur top/left/right). */
export function isExteriorBuildingFace(
  matrix: HeightMatrix,
  x: number,
  y: number,
  z: number,
  face: BuildingFace,
): boolean {
  const colH = heightAt(matrix, x, y);
  if (z < 0 || z >= colH) return false;
  switch (face) {
    case "top":
      return z + 1 >= colH;
    case "bottom":
      return z === 0;
    case "left":
      return z >= heightAt(matrix, x - 1, y);
    case "right":
      return z >= heightAt(matrix, x, y - 1);
    case "front":
      return y === 0 || z >= heightAt(matrix, x, y - 1);
    case "back": {
      const rows = matrix.length;
      return y === rows - 1 || z >= heightAt(matrix, x, y + 1);
    }
    default:
      return false;
  }
}

export type Vec3 = [number, number, number];

/** Weltnormale der Fläche am Standard-Voxel (ohne Gruppendrehung). */
export function buildingFaceWorldNormal(face: BuildingFace): Vec3 {
  switch (face) {
    case "right":
      return [1, 0, 0];
    case "left":
      return [-1, 0, 0];
    case "top":
      return [0, 1, 0];
    case "bottom":
      return [0, -1, 0];
    case "front":
      return [0, 0, 1];
    case "back":
      return [0, 0, -1];
    default:
      return [0, 1, 0];
  }
}

/** Fläche zeigt zur Kamera (Blick von cameraPos auf voxelCenter). */
export function buildingFaceTowardCamera(
  face: BuildingFace,
  cameraPos: Vec3,
  voxelCenter: Vec3,
): boolean {
  const [nx, ny, nz] = buildingFaceWorldNormal(face);
  const dx = cameraPos[0] - voxelCenter[0];
  const dy = cameraPos[1] - voxelCenter[1];
  const dz = cameraPos[2] - voxelCenter[2];
  const len = Math.hypot(dx, dy, dz) || 1;
  const dot = (nx * dx + ny * dy + nz * dz) / len;
  return dot > 0.15;
}

export function buildingFaceId(x: number, y: number, z: number, face: BuildingFace): string {
  return faceId(x, y, z, face);
}

/** Dominante sichtbare Fläche am Würfel (z. B. 0,0,0) für Kap.-1-Aufgaben. */
export function dominantExteriorFaceTowardCamera(
  matrix: HeightMatrix,
  cameraPos: Vec3,
  voxel: { x: number; y: number; z: number } = { x: 0, y: 0, z: 0 },
): BuildingFace | null {
  const GAP = 1.02;
  const center: Vec3 = [voxel.x * GAP, voxel.z * GAP + 0.47, voxel.y * GAP];
  let best: BuildingFace | null = null;
  let bestDot = -Infinity;
  for (const face of BUILDING_FACE_NAMES) {
    if (!isExteriorBuildingFace(matrix, voxel.x, voxel.y, voxel.z, face)) continue;
    const [nx, ny, nz] = buildingFaceWorldNormal(face);
    const dx = cameraPos[0] - center[0];
    const dy = cameraPos[1] - center[1];
    const dz = cameraPos[2] - center[2];
    const len = Math.hypot(dx, dy, dz) || 1;
    const dot = (nx * dx + ny * dy + nz * dz) / len;
    if (dot > bestDot) {
      bestDot = dot;
      best = face;
    }
  }
  return bestDot > 0.1 ? best : null;
}
