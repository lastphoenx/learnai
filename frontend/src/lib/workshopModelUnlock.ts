import type { WorkshopModelMode } from "@/components/learn/buildingWorkshop/workshopModelTypes";
import { clampWorkshopMode, unlockedHintIds } from "@/lib/workshop/workshopCapabilities";
import { spatialSequenceModelUnlock } from "@/lib/workshop/spatialSequenceCapabilities";

/** @deprecated Import from `@/lib/workshop/workshopCapabilities` */
export const workshopUnlockedHintIds = unlockedHintIds;

/** @deprecated Import from `@/lib/workshop/spatialSequenceCapabilities` */
export const workshopModelUnlockForSpatialSequence = spatialSequenceModelUnlock;

export function clampWorkshopModelMode(
  mode: WorkshopModelMode,
  unlockedModes: WorkshopModelMode[],
): WorkshopModelMode {
  return clampWorkshopMode(mode, unlockedModes, "oblique");
}
