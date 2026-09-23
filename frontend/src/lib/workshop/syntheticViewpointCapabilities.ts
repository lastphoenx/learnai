import type { WorkshopModelMode } from "@/components/learn/buildingWorkshop/workshopModelTypes";
import type { WorkshopModelUnlockResult } from "@/lib/workshop/workshopCapabilities";

/** Kap. 6 Standort: Schrägansicht, dann Wahl mit Draufsicht am Plan. */
export type SyntheticViewpointWorkshopPhase = "inspect" | "choose";

export function syntheticViewpointWorkshopModelUnlock(params: {
  phase: SyntheticViewpointWorkshopPhase;
}): WorkshopModelUnlockResult<WorkshopModelMode> {
  const unlocked = new Set<WorkshopModelMode>(["oblique"]);
  if (params.phase === "choose") {
    unlocked.add("top");
    unlocked.add("occupancy");
  }
  const order: WorkshopModelMode[] = ["oblique", "top", "occupancy"];
  return {
    unlockedModes: order.filter((m) => unlocked.has(m)),
    showColumnInspector: false,
    solutionOverlayAllowed: false,
  };
}
