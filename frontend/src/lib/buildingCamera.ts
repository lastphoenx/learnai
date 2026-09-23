import type { BuildingSceneBounds, SpatialCameraPreset } from "@/lib/spatialCoordinates";
import { buildingSceneBounds } from "@/lib/spatialCoordinates";
import type { HeightMatrix } from "@/lib/isoBuilding";

export type CameraPose = {
  position: [number, number, number];
  target: [number, number, number];
  zoom: number;
};

const PRESET_DIRS: Record<
  Exclude<SpatialCameraPreset, "oblique">,
  [number, number, number]
> = {
  front: [0, 0, -1],
  back: [0, 0, 1],
  left: [-1, 0, 0],
  right: [1, 0, 0],
  top: [0, 1, 0],
  front_left: [-0.75, 0.35, -0.75],
  front_right: [0.75, 0.35, -0.75],
  back_left: [-0.75, 0.35, 0.75],
  back_right: [0.75, 0.35, 0.75],
};

function normalize3(v: [number, number, number]): [number, number, number] {
  const len = Math.hypot(v[0], v[1], v[2]) || 1;
  return [v[0] / len, v[1] / len, v[2] / len];
}

function poseFromDirection(
  bounds: BuildingSceneBounds,
  dir: [number, number, number],
): CameraPose {
  const d = normalize3(dir);
  const span = Math.max(bounds.width, bounds.depth, bounds.height, 1);
  const dist = span * 2.4 + 2.5;
  const { cx, cy, cz } = bounds;
  return {
    position: [cx + d[0] * dist, cy + d[1] * dist, cz + d[2] * dist],
    target: [cx, cy, cz],
    zoom: Math.min(72, Math.max(28, 52 - span * 2)),
  };
}

/** Schräge Ansicht von vorne-rechts-oben (vorne = negative Z, Raumvertrag). */
const OBLIQUE_DIR: [number, number, number] = [1, 1.28, -1];

export function cameraPoseForPreset(
  matrix: HeightMatrix,
  preset: SpatialCameraPreset = "oblique",
): CameraPose {
  const bounds = buildingSceneBounds(matrix);
  if (preset === "oblique") {
    return poseFromDirection(bounds, OBLIQUE_DIR);
  }
  return poseFromDirection(bounds, PRESET_DIRS[preset]);
}
