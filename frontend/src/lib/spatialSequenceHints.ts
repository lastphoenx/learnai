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

type InspectStage = Extract<SpatialSequenceStage, { type: "inspect" }>;

function isSecondCameraInspectStage(s: SpatialSequenceStage): s is InspectStage {
  return s.type === "inspect" && s.unlock_hint === "show_second_camera";
}

export function secondCameraPresetFromConfig(
  stages: SpatialSequenceStage[],
  secondCamera?: string,
): string {
  const fromStage = stages.find(isSecondCameraInspectStage);
  return fromStage?.camera || secondCamera || "front_right";
}
