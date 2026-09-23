import type { SpatialSequenceAnswer } from "@/lib/spatialSequence";
import type { WorkshopModelMode } from "@/components/learn/buildingWorkshop/workshopModelTypes";
import type { WorkshopModelUnlockResult } from "@/lib/workshop/workshopCapabilities";

export type SpatialSequenceWorkshopPhase = "inspect" | "decision" | "projections" | "hint_only";

export function spatialSequenceModelUnlock(params: {
  phase: SpatialSequenceWorkshopPhase;
  visibility: SpatialSequenceAnswer["visibility"] | null;
  unlockedHintIds: string[];
}): WorkshopModelUnlockResult<WorkshopModelMode> {
  const unlocked = new Set<WorkshopModelMode>(["oblique"]);

  if (params.phase === "projections") {
    if (params.visibility === "second_view_required") {
      unlocked.add("second");
    }
    for (const id of params.unlockedHintIds) {
      if (id === "show_second_camera") unlocked.add("second");
      if (id === "show_top_view") {
        unlocked.add("top");
        unlocked.add("occupancy");
      }
      if (id === "show_solution_overlay") {
        unlocked.add("heights");
      }
    }
  }

  if (params.phase === "hint_only") {
    unlocked.add("top");
  }

  const solutionOverlayAllowed = params.unlockedHintIds.includes("show_solution_overlay");
  const showColumnInspector = solutionOverlayAllowed;

  const order: WorkshopModelMode[] = ["oblique", "second", "top", "occupancy", "heights"];
  return {
    unlockedModes: order.filter((m) => unlocked.has(m)),
    showColumnInspector,
    solutionOverlayAllowed,
  };
}
