import { describe, expect, it } from "vitest";
import { buildingProjections } from "@/lib/buildingProjections";

describe("buildingProjections", () => {
  it("matches backend top-down front/right orientation for asymmetric 4x4", () => {
    const matrix = [
      [1, 0, 3, 1],
      [2, 2, 1, 0],
      [0, 1, 2, 1],
      [1, 0, 1, 2],
    ];
    const views = buildingProjections(matrix);
    expect(views.front).toEqual([
      [0, 0, 1, 0],
      [1, 1, 1, 1],
      [1, 1, 1, 1],
    ]);
    expect(views.right).toEqual([
      [1, 0, 0, 0],
      [1, 1, 1, 1],
      [1, 1, 1, 1],
    ]);
  });
});
