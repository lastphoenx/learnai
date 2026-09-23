"use client";

import { useMemo, useState } from "react";
import type { TrainerSpatialSequenceConfig } from "@/lib/api";
import type { SpatialCameraPreset } from "@/lib/spatialCoordinates";
import { buildingProjections } from "@/lib/buildingProjections";
import { BuildingThreeCanvas } from "@/components/learn/BuildingThreeCanvas";
import { ProjectionFillGrids } from "@/components/learn/ProjectionFillGrids";
import { emptyProjectionDraft, type SpatialSequenceAnswer, type SpatialSequenceStage } from "@/lib/spatialSequence";
import {
  canUnlockSpatialHint,
  secondCameraPresetFromConfig,
  spatialSequenceProjectionIndex,
} from "@/lib/spatialSequenceHints";

type Props = {
  config: TrainerSpatialSequenceConfig;
  busy: boolean;
  result: { correct: boolean } | null;
  onSubmit: (answerJson: string) => void;
  onContinue: () => void;
};

const HINT_LABELS: Record<string, string> = {
  show_second_camera: "Zweite Kamera zeigen",
  show_top_view: "Aufsicht als Kamera",
  show_solution_overlay: "Lösung andeuten",
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

export function SpatialSequenceExercise({ config, busy, result, onSubmit, onContinue }: Props) {
  const matrix = config.height_matrix;
  const stages = (config.stages ?? []) as SpatialSequenceStage[];
  const hints = config.hints ?? [];

  const [stageIndex, setStageIndex] = useState(0);
  const [unlockedHints, setUnlockHints] = useState(0);
  const [visibility, setVisibility] = useState<SpatialSequenceAnswer["visibility"] | null>(null);
  const [projections, setProjections] = useState(emptyProjectionDraft());
  const [overlayHint, setOverlayHint] = useState(false);
  const [hintPreviewCamera, setHintPreviewCamera] = useState<SpatialCameraPreset | null>(null);

  const solutionOverlay = useMemo(() => (overlayHint ? buildingProjections(matrix) : null), [overlayHint, matrix]);

  const current = stages[stageIndex];
  const stageCamera: SpatialCameraPreset =
    (current?.type === "inspect" ? (current.camera as SpatialCameraPreset) : "oblique") ?? "oblique";
  const cameraLocked = current?.type === "inspect" ? Boolean(current.camera_locked) : false;

  const projectionStageIndex = spatialSequenceProjectionIndex(stages);

  const primaryFillCamera = useMemo((): SpatialCameraPreset => {
    const mainInspect = stages.find((s) => s.type === "inspect" && !s.hint_only);
    const cam = mainInspect?.camera ?? config.first_camera ?? "oblique";
    return cam as SpatialCameraPreset;
  }, [stages, config.first_camera]);

  const buildingFootprint = useMemo(() => {
    const rows = matrix.length;
    const cols = matrix[0]?.length ?? 1;
    const maxH = Math.max(...matrix.flat(), 1);
    return { rows, cols, maxH };
  }, [matrix]);

  const projectionViewCaptions = useMemo(
    () => ({
      front: `${buildingFootprint.maxH} Zeilen (Höhe) × ${buildingFootprint.cols} Spalten (Breite von vorne)`,
      right: `${buildingFootprint.maxH} Zeilen (Höhe) × ${buildingFootprint.rows} Spalten (Tiefe — von rechts gesehen, nicht die Vorderbreite)`,
      top: `${buildingFootprint.rows} Zeilen × ${buildingFootprint.cols} Spalten (Grundriss von oben)`,
    }),
    [buildingFootprint],
  );

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

  const nextHintId = hints[unlockedHints];
  const nextHintAllowed =
    nextHintId &&
    canUnlockSpatialHint(nextHintId, stageIndex, visibility, stages);

  function unlockNextHint() {
    const id = hints[unlockedHints];
    if (!id || !canUnlockSpatialHint(id, stageIndex, visibility, stages)) {
      return;
    }
    setUnlockHints((n) => Math.min(n + 1, hints.length));
    if (id === "show_solution_overlay") {
      setOverlayHint(true);
      return;
    }
    if (id === "show_second_camera") {
      setHintPreviewCamera(
        secondCameraPresetFromConfig(stages, config.second_camera) as SpatialCameraPreset,
      );
      return;
    }
    if (id === "show_top_view") {
      setHintPreviewCamera("top");
    }
  }

  function advanceStage() {
    const next = nextStageIndex(stages, stageIndex);
    if (next < stages.length) setStageIndex(next);
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

  return (
    <div className="spatial-sequence-exercise stack">
      {current?.type === "inspect" && (
        <>
          <p className="muted">Schritt {stageIndex + 1}: Gebäude untersuchen.</p>
          <BuildingThreeCanvas
            matrix={matrix}
            cameraPreset={stageCamera}
            cameraLocked={cameraLocked}
            showOrientationLabels={true}
            heightPx={280}
          />
          {!current.hint_only && (
            <button type="button" className="btn btn-secondary" onClick={advanceStage} disabled={!!result}>
              Weiter
            </button>
          )}
          {current.hint_only && (
            <button
              type="button"
              className="btn btn-secondary"
              onClick={() => setStageIndex(projectionStageIndex >= 0 ? projectionStageIndex : stageIndex)}
              disabled={!!result}
            >
              Zurück zu den Ansichten
            </button>
          )}
        </>
      )}

      {current?.type === "visibility_decision" && (
        <>
          <p>Reicht die erste Sicht, um alle wichtigen Informationen zu erkennen?</p>
          <div className="spatial-seq-choices">
            <button
              type="button"
              className={`btn${visibility === "one_view_sufficient" ? " btn-primary" : ""}`}
              disabled={!!result}
              onClick={() => {
                setVisibility("one_view_sufficient");
                advanceStage();
              }}
            >
              Eine Sicht reicht
            </button>
            <button
              type="button"
              className={`btn${visibility === "second_view_required" ? " btn-primary" : ""}`}
              disabled={!!result}
              onClick={() => {
                setVisibility("second_view_required");
                advanceStage();
              }}
            >
              Zweite Sicht nötig
            </button>
          </div>
        </>
      )}

      {current?.type === "projection_fill" && (
        <>
          <p>Trage die drei Ansichten ein (0 = leer, 1 = belegt bei Vorder-/Rechtsansicht).</p>
          <div className="spatial-seq-fill-workspace">
            <div className="spatial-seq-fill-building stack">
              <p className="muted">
                {hintPreviewCamera
                  ? "Hilfe — zusätzliche Ansicht zum Vergleichen"
                  : "Gebäude zum Vergleich (drehen und zoomen)"}
              </p>
              <BuildingThreeCanvas
                matrix={matrix}
                cameraPreset={hintPreviewCamera ?? primaryFillCamera}
                cameraLocked={Boolean(hintPreviewCamera)}
                showOrientationLabels={true}
                heightPx={220}
              />
              {hintPreviewCamera ? (
                <button
                  type="button"
                  className="btn btn-sm btn-secondary"
                  onClick={() => setHintPreviewCamera(null)}
                >
                  Hilfe schliessen
                </button>
              ) : null}
            </div>
            <ProjectionFillGrids
              views={{
                top: viewTemplates.views.top,
                front: viewTemplates.views.front,
                right: viewTemplates.views.right,
              }}
              editable={!result}
              values={projections}
              onChange={setProjections}
              solutionOverlay={solutionOverlay}
              viewCaptions={projectionViewCaptions}
            />
          </div>
        </>
      )}

      {hintPreviewCamera && current?.type !== "projection_fill" && (
        <div className="spatial-hint-preview stack">
          <p className="muted">Hilfe — zusätzliche Ansicht</p>
          <BuildingThreeCanvas
            matrix={matrix}
            cameraPreset={hintPreviewCamera}
            cameraLocked={true}
            showOrientationLabels={true}
            heightPx={220}
          />
          <button type="button" className="btn btn-sm btn-secondary" onClick={() => setHintPreviewCamera(null)}>
            Hilfe schliessen
          </button>
        </div>
      )}

      {hints.length > 0 && !result && (
        <div className="spatial-seq-hints">
          {unlockedHints < hints.length && (
            <button
              type="button"
              className="btn btn-sm btn-secondary"
              onClick={unlockNextHint}
              disabled={!nextHintAllowed}
              title={
                nextHintAllowed
                  ? undefined
                  : "Diese Hilfe ist an diesem Schritt noch nicht verfügbar."
              }
            >
              Hilfe: {HINT_LABELS[nextHintId ?? ""] ?? nextHintId}
            </button>
          )}
        </div>
      )}

      {canSubmit && !result && (
        <button type="button" className="btn btn-primary" disabled={busy} onClick={handleSubmit}>
          Antwort prüfen
        </button>
      )}

      {result && (
        <div className={`practice-result${result.correct ? " ok" : " bad"}`}>
          <p>{result.correct ? "Richtig!" : "Noch nicht vollständig richtig."}</p>
          <button type="button" className="btn btn-primary" onClick={onContinue}>
            Weiter
          </button>
        </div>
      )}
    </div>
  );
}
