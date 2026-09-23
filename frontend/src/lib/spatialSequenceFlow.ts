import type { SpatialSequenceAnswer, SpatialSequenceStage } from "@/lib/spatialSequence";

export type VisibilityBranch = {
  stages?: SpatialSequenceStage[];
  hints?: string[];
};

export type SpatialSequenceFlowConfig = {
  stages?: SpatialSequenceStage[];
  stages_prefix?: SpatialSequenceStage[];
  visibility_branches?: {
    one_view_sufficient?: VisibilityBranch;
    second_view_required?: VisibilityBranch;
  };
  hints?: string[];
};

export function spatialSequencePrefix(config: SpatialSequenceFlowConfig): SpatialSequenceStage[] {
  if (config.stages_prefix?.length) {
    return config.stages_prefix;
  }
  const stages = config.stages ?? [];
  const decisionIdx = stages.findIndex((s) => s.type === "visibility_decision");
  if (decisionIdx < 0) {
    return stages;
  }
  return stages.slice(0, decisionIdx + 1);
}

export function activeSpatialSequenceStages(
  config: SpatialSequenceFlowConfig,
  visibility: SpatialSequenceAnswer["visibility"] | null,
): SpatialSequenceStage[] {
  const prefix = spatialSequencePrefix(config);
  if (!visibility || !config.visibility_branches) {
    return config.stages?.length ? config.stages : prefix;
  }
  const branch =
    visibility === "one_view_sufficient"
      ? config.visibility_branches.one_view_sufficient
      : config.visibility_branches.second_view_required;
  return [...prefix, ...(branch?.stages ?? [])];
}

/** Vor der Sicht-Entscheidung nur Prefix — kein versteckter Zweitkamera-Schritt. */
export function navigableSpatialSequenceStages(
  config: SpatialSequenceFlowConfig,
  visibility: SpatialSequenceAnswer["visibility"] | null,
): SpatialSequenceStage[] {
  if (!visibility && config.visibility_branches) {
    return spatialSequencePrefix(config);
  }
  return activeSpatialSequenceStages(config, visibility);
}

export function activeSpatialSequenceHints(
  config: SpatialSequenceFlowConfig,
  visibility: SpatialSequenceAnswer["visibility"] | null,
): string[] {
  if (visibility && config.visibility_branches) {
    const branch =
      visibility === "one_view_sufficient"
        ? config.visibility_branches.one_view_sufficient
        : config.visibility_branches.second_view_required;
    return branch?.hints?.length ? branch.hints : (config.hints ?? []);
  }
  return config.hints ?? [];
}
