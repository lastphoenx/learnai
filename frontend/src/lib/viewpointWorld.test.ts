import { describe, expect, it } from "vitest";
import { planNormToLocalPosition, resolveViewpointNorm } from "@/lib/viewpointWorld";

describe("viewpointWorld", () => {
  it("resolves fallback norm for id A", () => {
    const [x, y] = resolveViewpointNorm({ id: "A" });
    expect(x).toBe(0.5);
    expect(y).toBe(0.9);
  });

  it("places vorne marker south of center on z", () => {
    const [, , z] = planNormToLocalPosition(0.5, 0.9, 3, 2);
    const [, , zCenter] = planNormToLocalPosition(0.5, 0.5, 3, 2);
    expect(z).toBeGreaterThan(zCenter);
  });
});
