import { describe, expect, it } from "vitest";
import { listVoxelsFromHeightMatrix } from "./voxelList";

function key(v: { gx: number; gy: number; gz: number }) {
  return `${v.gx},${v.gy},${v.gz}`;
}

describe("listVoxelsFromHeightMatrix", () => {
  it("renders every cube for height > 0 including iso-occluded cells", () => {
    const matrix = [[0, 1, 0], [1, 2, 0], [0, 0, 0]];
    const voxels = listVoxelsFromHeightMatrix(matrix);
    const keys = new Set(voxels.map(key));
    expect(keys.has("1,1,0")).toBe(true);
    expect(voxels.length).toBe(4);
  });

  it("skips zero-height cells", () => {
    const matrix = [[0, 1], [0, 0]];
    const voxels = listVoxelsFromHeightMatrix(matrix);
    expect(voxels).toEqual([{ gx: 1, gy: 0, gz: 0 }]);
  });
});
