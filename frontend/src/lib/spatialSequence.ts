export type SpatialSequenceAnswer = {
  visibility: "one_view_sufficient" | "second_view_required";
  projections: {
    top?: number[][];
    front?: number[][];
    right?: number[][];
  };
};

export function emptyProjectionDraft(): SpatialSequenceAnswer["projections"] {
  return {};
}

export type SpatialSequenceStage =
  | { type: "inspect"; camera?: string; camera_locked?: boolean; unlock_hint?: string }
  | { type: "visibility_decision" }
  | { type: "projection_fill"; views?: string[] };
