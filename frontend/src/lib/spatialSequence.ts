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
  | {
      type: "inspect";
      camera?: string;
      camera_locked?: boolean;
      unlock_hint?: string;
      hint_only?: boolean;
    }
  | { type: "visibility_decision" }
  | { type: "projection_fill"; views?: string[]; grid_size_hint?: "given" | "derive" };
