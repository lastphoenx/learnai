/**
 * Raumvertrag — muss mit backend/app/core/spatial_coordinates.py übereinstimmen.
 */

import type { HeightMatrix } from "@/lib/isoBuilding";

export const SPATIAL_GAP = 1.02;

export const SPATIAL_COORDINATE_SYSTEM = {
  frontRow: 0,
  xDirection: "left-to-right" as const,
  yDirection: "front-to-back" as const,
  zDirection: "bottom-to-top" as const,
};

export type SpatialCameraPreset =
  | "oblique"
  | "front"
  | "back"
  | "left"
  | "right"
  | "top"
  | "front_left"
  | "front_right"
  | "back_left"
  | "back_right";

export type BuildingSceneBounds = {
  cx: number;
  cy: number;
  cz: number;
  width: number;
  depth: number;
  height: number;
};

export function buildingSceneBounds(matrix: HeightMatrix): BuildingSceneBounds {
  const cols = matrix[0]?.length ?? 1;
  const rows = matrix.length;
  let maxH = 1;
  for (const row of matrix) {
    for (const h of row) {
      if (h > maxH) maxH = h;
    }
  }
  const width = Math.max(SPATIAL_GAP, (cols - 1) * SPATIAL_GAP + 0.94);
  const depth = Math.max(SPATIAL_GAP, (rows - 1) * SPATIAL_GAP + 0.94);
  const height = maxH * SPATIAL_GAP;
  return {
    cx: 0,
    cy: height / 2,
    cz: 0,
    width,
    depth,
    height,
  };
}
