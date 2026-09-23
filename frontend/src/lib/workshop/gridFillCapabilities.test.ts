import { describe, expect, it } from "vitest";
import { gridFillWorkshopModelUnlock } from "@/lib/workshop/gridFillCapabilities";

describe("gridFillWorkshopModelUnlock", () => {
  it("inspect: nur Schrägansicht", () => {
    const r = gridFillWorkshopModelUnlock({ phase: "inspect" });
    expect(r.unlockedModes).toEqual(["oblique"]);
  });

  it("plan: Schräg und Draufsicht", () => {
    const r = gridFillWorkshopModelUnlock({ phase: "plan" });
    expect(r.unlockedModes).toEqual(["oblique", "top"]);
  });
});
