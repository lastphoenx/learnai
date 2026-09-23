import type { SpatialSequenceStage } from "@/lib/spatialSequence";

export function spatialSequenceDecisionIndex(stages: SpatialSequenceStage[]): number {
  return stages.findIndex((s) => s.type === "visibility_decision");
}

export function spatialSequenceProjectionIndex(stages: SpatialSequenceStage[]): number {
  return stages.findIndex((s) => s.type === "projection_fill");
}

/** Hilfen ändern den Stufenindex nicht — nur erlaubte Zeitpunkte. */
export function canUnlockSpatialHint(
  hintId: string,
  stageIndex: number,
  visibility: string | null,
  stages: SpatialSequenceStage[],
): boolean {
  const decisionIdx = spatialSequenceDecisionIndex(stages);
  const projectionIdx = spatialSequenceProjectionIndex(stages);
  const pastDecision = visibility !== null || (decisionIdx >= 0 && stageIndex > decisionIdx);

  if (hintId === "show_second_camera") {
    return pastDecision;
  }
  if (hintId === "show_top_view") {
    return projectionIdx >= 0 && stageIndex >= projectionIdx;
  }
  if (hintId === "show_solution_overlay") {
    return projectionIdx >= 0 && stageIndex >= projectionIdx;
  }
  return false;
}

export function secondCameraPresetFromConfig(
  stages: SpatialSequenceStage[],
  secondCamera?: string,
): string {
  const fromStage = stages.find(
    (s) => s.type === "inspect" && s.unlock_hint === "show_second_camera",
  )?.camera;
  return fromStage || secondCamera || "front_right";
}
