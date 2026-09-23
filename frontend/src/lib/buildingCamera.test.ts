import { describe, expect, it } from "vitest";
import { cameraPoseForPreset } from "@/lib/buildingCamera";
import { SPATIAL_COORDINATE_SYSTEM } from "@/lib/spatialCoordinates";

describe("spatial coordinate contract", () => {
  it("front row is zero", () => {
    expect(SPATIAL_COORDINATE_SYSTEM.frontRow).toBe(0);
  });
});

describe("cameraPoseForPreset", () => {
  const matrix = [[1, 2], [1, 0]];

  it("front camera sits on negative Z side of building center", () => {
    const pose = cameraPoseForPreset(matrix, "front");
    expect(pose.position[2]).toBeLessThan(pose.target[2]);
  });

  it("top camera sits above target", () => {
    const pose = cameraPoseForPreset(matrix, "top");
    expect(pose.position[1]).toBeGreaterThan(pose.target[1]);
  });

  it("oblique preset returns finite pose", () => {
    const pose = cameraPoseForPreset(matrix, "oblique");
    expect(pose.zoom).toBeGreaterThan(0);
    expect(Number.isFinite(pose.position[0])).toBe(true);
  });
});
