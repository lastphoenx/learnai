import { describe, expect, it } from "vitest";
import { workshopModelUnlockForSpatialSequence } from "@/lib/workshopModelUnlock";

describe("workshopModelUnlockForSpatialSequence", () => {
  it("inspect: nur Schrägansicht", () => {
    const r = workshopModelUnlockForSpatialSequence({
      phase: "inspect",
      visibility: null,
      unlockedHintIds: [],
    });
    expect(r.unlockedModes).toEqual(["oblique"]);
    expect(r.solutionOverlayAllowed).toBe(false);
  });

  it("decision: noch keine starke Hilfe", () => {
    const r = workshopModelUnlockForSpatialSequence({
      phase: "decision",
      visibility: null,
      unlockedHintIds: [],
    });
    expect(r.unlockedModes).toEqual(["oblique"]);
  });

  it("projections + zweite Sicht nötig: Schräg und zweite Kamera", () => {
    const r = workshopModelUnlockForSpatialSequence({
      phase: "projections",
      visibility: "second_view_required",
      unlockedHintIds: [],
    });
    expect(r.unlockedModes).toContain("second");
    expect(r.unlockedModes).not.toContain("heights");
  });

  it("nach show_top_view: Draufsicht und Belegung", () => {
    const r = workshopModelUnlockForSpatialSequence({
      phase: "projections",
      visibility: "one_view_sufficient",
      unlockedHintIds: ["show_top_view"],
    });
    expect(r.unlockedModes).toEqual(["oblique", "top", "occupancy"]);
  });

  it("nach show_solution_overlay: Höhenplan, kein Overlay ohne Flag", () => {
    const r = workshopModelUnlockForSpatialSequence({
      phase: "projections",
      visibility: "one_view_sufficient",
      unlockedHintIds: ["show_top_view", "show_solution_overlay"],
    });
    expect(r.unlockedModes).toContain("heights");
    expect(r.solutionOverlayAllowed).toBe(true);
    expect(r.showColumnInspector).toBe(true);
  });
});
