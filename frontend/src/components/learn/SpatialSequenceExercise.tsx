"use client";

import { useMemo, useState } from "react";
import type { TrainerSpatialSequenceConfig } from "@/lib/api";
import type { SpatialCameraPreset } from "@/lib/spatialCoordinates";
import { buildingProjections } from "@/lib/buildingProjections";
import { ProjectionFillGrids } from "@/components/learn/ProjectionFillGrids";
import { BuildingViewsWorkshopShell } from "@/components/learn/buildingWorkshop/BuildingViewsWorkshopShell";
import { BuildingWorkshopModelPanel } from "@/components/learn/buildingWorkshop/BuildingWorkshopModelPanel";
import { VisibilityDecisionPanel } from "@/components/learn/buildingWorkshop/VisibilityDecisionPanel";
import { emptyProjectionDraft, type SpatialSequenceAnswer, type SpatialSequenceStage } from "@/lib/spatialSequence";
import {
  emptyNumberGrid,
  normalizeGridSizeHint,
  type ViewSize,
} from "@/lib/spatialGridSize";
import {
  canUnlockSpatialHint,
  secondCameraPresetFromConfig,
  spatialSequenceProjectionIndex,
} from "@/lib/spatialSequenceHints";
import {
  activeSpatialSequenceHints,
  navigableSpatialSequenceStages,
  spatialSequencePrefix,
} from "@/lib/spatialSequenceFlow";
import { heightMatrixHasVoxels } from "@/lib/isoBuilding";

type Props = {
  config: TrainerSpatialSequenceConfig;
  busy: boolean;
  result: {
    correct: boolean;
    label_slots?: Array<{
      id: string;
      correct: boolean;
      expected_term?: string | null;
      user_term?: string | null;
    }> | null;
  } | null;
  onSubmit: (answerJson: string) => void;
  onContinue: () => void;
};

const HINT_LABELS: Record<string, string> = {
  show_second_camera: "Zweite Kamera zeigen",
  show_top_view: "Aufsicht als Kamera",
  show_solution_overlay: "Lösung überlagern",
};

function isSkippableStage(stage: SpatialSequenceStage | undefined): boolean {
  return Boolean(stage && stage.type === "inspect" && stage.hint_only);
}

function nextStageIndex(stages: SpatialSequenceStage[], from: number): number {
  let i = from + 1;
  while (i < stages.length && isSkippableStage(stages[i])) {
    i += 1;
  }
  return i;
}

type InspectStage = Extract<SpatialSequenceStage, { type: "inspect" }>;

function asInspectStage(stage: SpatialSequenceStage | undefined): InspectStage | undefined {
  return stage?.type === "inspect" ? stage : undefined;
}

function useWorkshopPhase(
  current: SpatialSequenceStage | undefined,
  stageIndex: number,
  projectionStageIndex: number,
): "inspect" | "decision" | "projections" | "hint_only" {
  if (current?.type === "inspect" && current.hint_only) return "hint_only";
  if (current?.type === "visibility_decision") return "decision";
  if (current?.type === "projection_fill" || stageIndex >= projectionStageIndex) return "projections";
  return "inspect";
}

export function SpatialSequenceExercise({ config, busy, result, onSubmit, onContinue }: Props) {
  const matrix = config.height_matrix;
  const hasBuilding = heightMatrixHasVoxels(matrix);
  const flowConfig = config;
  const [stageIndex, setStageIndex] = useState(0);
  const [unlockedHints, setUnlockHints] = useState(0);
  const [visibility, setVisibility] = useState<SpatialSequenceAnswer["visibility"] | null>(null);
  const stages = useMemo(
    () => navigableSpatialSequenceStages(flowConfig, visibility) as SpatialSequenceStage[],
    [flowConfig, visibility],
  );
  const hints = useMemo(() => activeSpatialSequenceHints(flowConfig, visibility), [flowConfig, visibility]);
  const [projections, setProjections] = useState(emptyProjectionDraft());
  const [overlayHint, setOverlayHint] = useState(false);

  const solutionOverlay = useMemo(() => (overlayHint ? buildingProjections(matrix) : null), [overlayHint, matrix]);

  const current = stages[stageIndex];
  const projectionStageIndex = spatialSequenceProjectionIndex(stages);
  const phase = useWorkshopPhase(current, stageIndex, projectionStageIndex);

  const projectionFillStage = stages.find((s) => s.type === "projection_fill");
  const gridSizeHint = normalizeGridSizeHint(
    projectionFillStage?.type === "projection_fill" ? projectionFillStage.grid_size_hint : undefined,
  );

  const [viewSizes, setViewSizes] = useState<Partial<Record<"front" | "right" | "top", ViewSize>>>(() => {
    const views = projectionFillStage?.views ?? ["front", "right", "top"];
    const initial: Partial<Record<"front" | "right" | "top", ViewSize>> = {};
    for (const key of views) {
      if (key === "front" || key === "right" || key === "top") {
        initial[key] = { rows: 1, cols: 1 };
      }
    }
    return initial;
  });

  const firstCamera = (config.first_camera ?? "oblique") as SpatialCameraPreset;
  const secondCamera = useMemo(
    () => secondCameraPresetFromConfig(stages, config.second_camera) as SpatialCameraPreset,
    [stages, config.second_camera],
  );

  const expectedVisibility = config.expected_visibility;

  const buildingFootprint = useMemo(() => {
    const rows = matrix.length;
    const cols = matrix[0]?.length ?? 1;
    const maxH = Math.max(...matrix.flat(), 1);
    return { rows, cols, maxH };
  }, [matrix]);

  const projectionViewCaptions = useMemo(() => {
    if (gridSizeHint === "derive") {
      return {
        front: "Silhouette von vorne markieren.",
        right: "Silhouette von rechts markieren.",
        top: "Grundriss: belegte Felder (ohne Höhenzahl).",
      };
    }
    return {
      front: `${buildingFootprint.maxH}×${buildingFootprint.cols} — von vorne`,
      right: `${buildingFootprint.maxH}×${buildingFootprint.rows} — von rechts`,
      top: `${buildingFootprint.rows}×${buildingFootprint.cols} — Aufsicht (Belegung)`,
    };
  }, [buildingFootprint, gridSizeHint]);

  const viewTemplates = useMemo(() => {
    const pf = stages.find((s) => s.type === "projection_fill");
    const views = pf?.views ?? ["front", "right", "top"];
    const rows = matrix.length;
    const cols = matrix[0]?.length ?? 1;
    const maxH = Math.max(...matrix.flat(), 1);
    const draft = emptyProjectionDraft();
    return {
      views: {
        top: draft.top ?? Array.from({ length: rows }, () => Array.from({ length: cols }, () => 0)),
        front: draft.front ?? Array.from({ length: maxH }, () => Array.from({ length: cols }, () => 0)),
        right: draft.right ?? Array.from({ length: maxH }, () => Array.from({ length: rows }, () => 0)),
      },
      keys: views as ("front" | "right" | "top")[],
    };
  }, [matrix, stages]);

  const displayViews = useMemo(() => {
    if (gridSizeHint === "given") {
      return viewTemplates.views;
    }
    const out: { top?: number[][]; front?: number[][]; right?: number[][] } = {};
    for (const key of viewTemplates.keys) {
      const sz = viewSizes[key] ?? { rows: 1, cols: 1 };
      out[key] = emptyNumberGrid(sz.rows, sz.cols);
    }
    return out;
  }, [gridSizeHint, viewSizes, viewTemplates]);

  function handleViewSizeChange(view: "front" | "right" | "top", size: ViewSize) {
    setViewSizes((prev) => ({ ...prev, [view]: size }));
    setProjections((prev) => ({
      ...prev,
      [view]: emptyNumberGrid(size.rows, size.cols),
    }));
  }

  const nextHintId = hints[unlockedHints];
  const nextHintAllowed =
    nextHintId && canUnlockSpatialHint(nextHintId, stageIndex, visibility, stages);

  function unlockNextHint() {
    const id = hints[unlockedHints];
    if (!id || !canUnlockSpatialHint(id, stageIndex, visibility, stages)) {
      return;
    }
    setUnlockHints((n) => Math.min(n + 1, hints.length));
    if (id === "show_solution_overlay") {
      setOverlayHint(true);
    }
  }

  function advanceStage() {
    const next = nextStageIndex(stages, stageIndex);
    if (next < stages.length) setStageIndex(next);
  }

  function clearProjections() {
    setProjections(emptyProjectionDraft());
    setOverlayHint(false);
  }

  const canSubmit =
    visibility !== null && stageIndex >= projectionStageIndex && projectionStageIndex >= 0;

  function handleSubmit() {
    const payload: SpatialSequenceAnswer = {
      visibility: visibility ?? "one_view_sufficient",
      projections,
    };
    onSubmit(JSON.stringify(payload));
  }

  if (!hasBuilding) {
    return (
      <div className="spatial-sequence-exercise stack">
        <div className="learn-feedback bad" role="alert">
          <strong>Gebäudedaten fehlen</strong>
          <p className="muted" style={{ margin: "0.35rem 0 0" }}>
            Der Höhenplan ist leer oder ungültig — diese Aufgabe kann nicht bearbeitet werden.
          </p>
        </div>
      </div>
    );
  }

  if (phase === "hint_only") {
    const hintStage = asInspectStage(current);
    return (
      <div className="spatial-sequence-exercise stack">
        <p className="muted">Hilfe — zusätzliche Ansicht</p>
        <BuildingWorkshopModelPanel
          matrix={matrix}
          firstCamera={(hintStage?.camera as SpatialCameraPreset) ?? "top"}
          secondCamera={secondCamera}
          cameraLocked={true}
        />
        <button
          type="button"
          className="btn btn-secondary"
          onClick={() => setStageIndex(projectionStageIndex >= 0 ? projectionStageIndex : stageIndex)}
          disabled={!!result}
        >
          Zurück zu den Ansichten
        </button>
      </div>
    );
  }

  const showDecision = phase === "decision" || phase === "projections";
  const showProjections = phase === "projections";
  const modelDisabled = !!result;

  return (
    <div className="spatial-sequence-exercise">
      <BuildingViewsWorkshopShell
        taskTitle="Ansichten eines Gebäudes"
        taskPrompt="Erst untersuchen, dann entscheiden, dann die drei Orthogonalansichten markieren."
        instruction={
          phase === "inspect"
            ? "Schritt 1: Untersuche das Gebäude in der Schrägansicht. Nutze die Werkzeugleiste (zweite Sicht, von oben, Höhenplan)."
            : null
        }
        modelPanel={
          <BuildingWorkshopModelPanel
            matrix={matrix}
            firstCamera={firstCamera}
            secondCamera={secondCamera}
            cameraLocked={true}
            disabled={modelDisabled}
          />
        }
        decisionBlock={
          showDecision
            ? (
                <VisibilityDecisionPanel
                  value={visibility}
                  expected={expectedVisibility}
                  disabled={!!result || phase === "projections"}
                  onPick={setVisibility}
                  showContinue={phase === "decision" && !result}
                  onContinue={() => setStageIndex(spatialSequencePrefix(flowConfig).length)}
                />
              )
            : undefined
        }
        projectionsBlock={
          showProjections
            ? (
                <ProjectionFillGrids
                  views={{
                    top: displayViews.top,
                    front: displayViews.front,
                    right: displayViews.right,
                  }}
                  editable={!result}
                  values={projections}
                  onChange={setProjections}
                  solutionOverlay={solutionOverlay}
                  viewCaptions={projectionViewCaptions}
                  gridSizeHint={gridSizeHint}
                  viewSizes={viewSizes}
                  onViewSizeChange={gridSizeHint === "derive" ? handleViewSizeChange : undefined}
                  slotFeedback={result?.label_slots ?? undefined}
                />
              )
            : undefined
        }
        helpBlock={
          showProjections && !result
            ? (
                <>
                  <div className="btnrow">
                    {hints.length > 0 && unlockedHints < hints.length && (
                      <button
                        type="button"
                        className="btn btn-sm btn-secondary"
                        onClick={unlockNextHint}
                        disabled={!nextHintAllowed}
                      >
                        Hilfe: {HINT_LABELS[nextHintId ?? ""] ?? nextHintId}
                      </button>
                    )}
                    <button
                      type="button"
                      className="btn btn-sm btn-secondary"
                      onClick={() => setOverlayHint((v) => !v)}
                    >
                      {overlayHint ? "Lösung ausblenden" : "Lösung überlagern"}
                    </button>
                  </div>
                  {overlayHint ? (
                    <div className="building-views-solution-legend" aria-hidden={false}>
                      <span><i className="mine" /> deine Auswahl</span>
                      <span><i className="missing" /> fehlt noch</span>
                      <span><i className="both" /> richtig gewählt</span>
                      <span><i className="extra" /> zu viel gewählt</span>
                    </div>
                  ) : null}
                </>
              )
            : undefined
        }
        actions={
          <>
            {phase === "inspect" && (
              <button type="button" className="btn btn-secondary" onClick={advanceStage} disabled={!!result}>
                Weiter zur Sicht-Entscheidung
              </button>
            )}
            {showProjections && !result && (
              <>
                <button type="button" className="btn-primary" disabled={busy || !canSubmit} onClick={handleSubmit}>
                  Ansichten prüfen
                </button>
                <button type="button" className="btn btn-secondary" disabled={busy} onClick={clearProjections}>
                  Leeren
                </button>
              </>
            )}
          </>
        }
        footer={
          result
            ? (
                <div className={`practice-result learn-feedback${result.correct ? " ok" : " bad"}`}>
                  <p>{result.correct ? "Richtig!" : "Noch nicht vollständig richtig."}</p>
                  <button type="button" className="btn btn-primary" onClick={onContinue}>
                    Weiter
                  </button>
                </div>
              )
            : null
        }
      />
    </div>
  );
}
