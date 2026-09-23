import { describe, expect, it } from "vitest";
import { resolveSpatialSequenceWorkshopPhase } from "@/lib/workshop/spatialSequenceWorkshopPhase";
import type { SpatialSequenceStage } from "@/lib/spatialSequence";

describe("resolveSpatialSequenceWorkshopPhase", () => {
  const inspect: SpatialSequenceStage = { type: "inspect", camera: "oblique" };
  const decision: SpatialSequenceStage = { type: "visibility_decision" };

  it("start ohne projection_fill in stages: inspect, nicht projections bei index -1", () => {
    expect(resolveSpatialSequenceWorkshopPhase(inspect, 0, -1)).toBe("inspect");
    expect(resolveSpatialSequenceWorkshopPhase(decision, 1, -1)).toBe("decision");
  });

  it("nach Freischaltung: projections ab projectionStageIndex", () => {
    const projection: SpatialSequenceStage = { type: "projection_fill", views: ["front", "right", "top"] };
    expect(resolveSpatialSequenceWorkshopPhase(projection, 2, 2)).toBe("projections");
    expect(resolveSpatialSequenceWorkshopPhase(decision, 1, 2)).toBe("decision");
  });
});
