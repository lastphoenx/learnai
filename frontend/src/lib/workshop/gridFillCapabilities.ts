import type { WorkshopModelMode } from "@/components/learn/buildingWorkshop/workshopModelTypes";
import type { WorkshopModelUnlockResult } from "@/lib/workshop/workshopCapabilities";

/** Kap. 4 Bauplan: erst Schrägansicht, dann Höhenplan mit Draufsicht-Hilfe. */
export type GridFillWorkshopPhase = "inspect" | "plan";

export function gridFillWorkshopModelUnlock(params: {
  phase: GridFillWorkshopPhase;
}): WorkshopModelUnlockResult<WorkshopModelMode> {
  const unlocked = new Set<WorkshopModelMode>(["oblique"]);
  if (params.phase === "plan") {
    unlocked.add("top");
  }
  const order: WorkshopModelMode[] = ["oblique", "top"];
  return {
    unlockedModes: order.filter((m) => unlocked.has(m)),
    showColumnInspector: false,
    solutionOverlayAllowed: false,
  };
}
