import { describe, expect, it } from "vitest";
import { cubeNetFoldLabels, validCubeNet } from "@/lib/cubeNetFold";

const CROSS: [number, number][] = [[0, 1], [1, 1], [2, 1], [1, 0], [1, 2], [1, 3]];

describe("cubeNetFold", () => {
  it("Kreuz-Netz ist gültig", () => {
    expect(validCubeNet(CROSS)).toBe(true);
    const labels = cubeNetFoldLabels(CROSS);
    expect(labels).not.toBeNull();
    expect(Object.keys(labels!).length).toBe(6);
    const unique = new Set(Object.values(labels!).map((v) => v.label));
    expect(unique.size).toBe(6);
  });

  it("2x3-Block ungültig", () => {
    const block: [number, number][] = [[0, 0], [1, 0], [2, 0], [0, 1], [1, 1], [2, 1]];
    expect(validCubeNet(block)).toBe(false);
  });
});
