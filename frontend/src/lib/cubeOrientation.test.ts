import { describe, expect, it } from "vitest";
import {
  BOX_MATERIAL_INDEX_TO_FACE,
  dominantExteriorFaceTowardCamera,
  isExteriorBuildingFace,
} from "@/lib/cubeOrientation";

describe("cubeOrientation", () => {
  it("Einzelwürfel: alle 6 Flächen äusserlich", () => {
    const m = [[1]];
    for (const face of ["top", "bottom", "left", "right", "front", "back"] as const) {
      expect(isExteriorBuildingFace(m, 0, 0, 0, face)).toBe(true);
    }
  });

  it("Materialindex-Mapping vollständig", () => {
    expect(BOX_MATERIAL_INDEX_TO_FACE[2]).toBe("top");
    expect(BOX_MATERIAL_INDEX_TO_FACE[4]).toBe("front");
  });

  it("dominantExteriorFaceTowardCamera von schräg oben", () => {
    const m = [[1]];
    const face = dominantExteriorFaceTowardCamera(m, [5, 8, 5], { x: 0, y: 0, z: 0 });
    expect(face).toBeTruthy();
  });
});
