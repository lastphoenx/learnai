import type { SpatialSequenceStage } from "@/lib/spatialSequence";

export type SpatialSequenceWorkshopPhase = "inspect" | "decision" | "projections" | "hint_only";

/** Phasen-Gating; projectionStageIndex -1 = noch keine Projektions-Stufe in der Navigation. */
export function resolveSpatialSequenceWorkshopPhase(
  current: SpatialSequenceStage | undefined,
  stageIndex: number,
  projectionStageIndex: number,
): SpatialSequenceWorkshopPhase {
  if (current?.type === "inspect" && current.hint_only) return "hint_only";
  if (current?.type === "visibility_decision") return "decision";
  if (current?.type === "projection_fill") return "projections";
  if (projectionStageIndex >= 0 && stageIndex >= projectionStageIndex) return "projections";
  return "inspect";
}
