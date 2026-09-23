import type { SpatialSequenceAnswer } from "@/lib/spatialSequence";
import type { WorkshopModelMode } from "@/components/learn/buildingWorkshop/workshopModelTypes";

export function workshopUnlockedHintIds(hints: string[], unlockedCount: number): string[] {
  return hints.slice(0, Math.max(0, unlockedCount));
}

export function workshopModelUnlockForSpatialSequence(params: {
  phase: "inspect" | "decision" | "projections" | "hint_only";
  visibility: SpatialSequenceAnswer["visibility"] | null;
  unlockedHintIds: string[];
}): {
  unlockedModes: WorkshopModelMode[];
  showColumnInspector: boolean;
  solutionOverlayAllowed: boolean;
} {
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

export function clampWorkshopModelMode(
  mode: WorkshopModelMode,
  unlockedModes: WorkshopModelMode[],
): WorkshopModelMode {
  if (unlockedModes.includes(mode)) return mode;
  return unlockedModes[0] ?? "oblique";
}
