import { describe, expect, it } from "vitest";
import {
  activeSpatialSequenceStages,
  navigableSpatialSequenceStages,
  spatialSequencePrefix,
} from "@/lib/spatialSequenceFlow";

const flow = {
  stages_prefix: [
    { type: "inspect" as const, camera: "oblique" },
    { type: "visibility_decision" as const },
  ],
  visibility_branches: {
    one_view_sufficient: {
      stages: [{ type: "projection_fill" as const, grid_size_hint: "given" as const }],
      hints: ["show_solution_overlay"],
    },
    second_view_required: {
      stages: [
        { type: "inspect" as const, camera: "front_right" },
        { type: "projection_fill" as const },
      ],
      hints: ["show_solution_overlay"],
    },
  },
};

describe("spatialSequenceFlow", () => {
  it("before decision only shows prefix", () => {
    expect(navigableSpatialSequenceStages(flow, null)).toHaveLength(2);
  });

  it("one_view skips mandatory second camera inspect", () => {
    const stages = activeSpatialSequenceStages(flow, "one_view_sufficient");
    expect(stages).toHaveLength(3);
    expect(stages[2]?.type).toBe("projection_fill");
  });

  it("second_view inserts required inspect", () => {
    const stages = activeSpatialSequenceStages(flow, "second_view_required");
    expect(stages).toHaveLength(4);
    expect(stages[2]?.type).toBe("inspect");
  });

  it("prefix length is 2", () => {
    expect(spatialSequencePrefix(flow)).toHaveLength(2);
  });
});
