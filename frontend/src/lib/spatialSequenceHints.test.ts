import { describe, expect, it } from "vitest";
import { canUnlockSpatialHint } from "@/lib/spatialSequenceHints";
import type { SpatialSequenceStage } from "@/lib/spatialSequence";

const STAGES: SpatialSequenceStage[] = [
  { type: "inspect", camera: "oblique" },
  { type: "visibility_decision" },
  { type: "inspect", camera: "front", unlock_hint: "show_second_camera" },
  { type: "projection_fill", views: ["front", "right", "top"] },
];

describe("canUnlockSpatialHint", () => {
  it("blocks second camera hint on first inspect stage", () => {
    expect(canUnlockSpatialHint("show_second_camera", 0, null, STAGES)).toBe(false);
  });

  it("allows second camera after visibility decision", () => {
    expect(canUnlockSpatialHint("show_second_camera", 1, "second_view_required", STAGES)).toBe(true);
  });

  it("allows solution overlay only on projection stage", () => {
    expect(canUnlockSpatialHint("show_solution_overlay", 0, null, STAGES)).toBe(false);
    expect(canUnlockSpatialHint("show_solution_overlay", 3, "second_view_required", STAGES)).toBe(true);
  });
});
