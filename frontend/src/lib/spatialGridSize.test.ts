import { describe, expect, it } from "vitest";
import { initialGridFillDimensions } from "@/lib/spatialGridSize";

describe("initialGridFillDimensions", () => {
  it("starts at 1x1 for derive so solution size is not revealed", () => {
    expect(initialGridFillDimensions(4, 5, "derive")).toEqual({ rows: 1, cols: 1 });
  });

  it("uses config dimensions for given", () => {
    expect(initialGridFillDimensions(4, 5, "given")).toEqual({ rows: 4, cols: 5 });
    expect(initialGridFillDimensions(4, 5, undefined)).toEqual({ rows: 4, cols: 5 });
  });
});
