"use client";

import { useMemo, useState } from "react";
import type { TrainerSpatialSequenceConfig } from "@/lib/api";
import type { SpatialCameraPreset } from "@/lib/spatialCoordinates";
import { buildingProjections } from "@/lib/buildingProjections";
import { BuildingThreeCanvas } from "@/components/learn/BuildingThreeCanvas";
import { ProjectionFillGrids } from "@/components/learn/ProjectionFillGrids";
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

type InspectStage = Extract<SpatialSequenceStage, { type: "inspect" }>;

function asInspectStage(stage: SpatialSequenceStage | undefined): InspectStage | undefined {
  return stage?.type === "inspect" ? stage : undefined;
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
  const [hintPreviewCamera, setHintPreviewCamera] = useState<SpatialCameraPreset | null>(null);

  const solutionOverlay = useMemo(() => (overlayHint ? buildingProjections(matrix) : null), [overlayHint, matrix]);

  const current = stages[stageIndex];
  const inspectStage = asInspectStage(current);
  const stageCamera: SpatialCameraPreset = (inspectStage?.camera as SpatialCameraPreset) ?? "oblique";
  const cameraLocked = Boolean(inspectStage?.camera_locked);

  const projectionStageIndex = spatialSequenceProjectionIndex(stages);
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

  const primaryFillCamera = useMemo((): SpatialCameraPreset => {
    const mainInspect = stages.find(
      (s): s is InspectStage => s.type === "inspect" && !s.hint_only,
    );
    const cam = mainInspect?.camera ?? config.first_camera ?? "oblique";
    return cam as SpatialCameraPreset;
  }, [stages, config.first_camera]);

  const buildingFootprint = useMemo(() => {
    const rows = matrix.length;
    const cols = matrix[0]?.length ?? 1;
    const maxH = Math.max(...matrix.flat(), 1);
    return { rows, cols, maxH };
  }, [matrix]);

  const projectionViewCaptions = useMemo(() => {
    if (gridSizeHint === "derive") {
      return {
        front: "Lege Zeilen (Höhe) und Spalten (Breite von vorne) fest, dann 0/1 eintragen.",
        right: "Spalten = Gebäudetiefe von der Seite (nicht die Vorderbreite).",
        top: "Zeilen und Spalten entsprechen dem Grundriss von oben.",
      };
    }
    return {
      front: `${buildingFootprint.maxH} Zeilen (Höhe) × ${buildingFootprint.cols} Spalten (Breite von vorne)`,
      right: `${buildingFootprint.maxH} Zeilen (Höhe) × ${buildingFootprint.rows} Spalten (Tiefe — von rechts gesehen, nicht die Vorderbreite)`,
      top: `${buildingFootprint.rows} Zeilen × ${buildingFootprint.cols} Spalten (Grundriss von oben)`,
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

  if (!hasBuilding) {
    return (
      <div className="spatial-sequence-exercise stack">
        <div className="learn-feedback bad" role="alert">
          <strong>Gebäudedaten fehlen</strong>
          <p className="muted" style={{ margin: "0.35rem 0 0" }}>
            Der Höhenplan ist leer oder ungültig — diese Aufgabe kann nicht bearbeitet werden. Einheit neu aufbereiten
            oder Didaktik prüfen.
          </p>
        </div>
      </div>
    );
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
          <p>
            Kannst du aus dieser ersten Ansicht wirklich alle wichtigen Stellen des Gebäudes erkennen — oder
            brauchst du zwingend noch eine zweite Perspektive?
          </p>
          <div className="spatial-seq-choices">
            <button
              type="button"
              className={`btn${visibility === "one_view_sufficient" ? " btn-primary" : ""}`}
              disabled={!!result}
              onClick={() => {
                setVisibility("one_view_sufficient");
                setStageIndex(spatialSequencePrefix(flowConfig).length);
              }}
            >
              Ja, eindeutig — eine Sicht reicht
            </button>
            <button
              type="button"
              className={`btn${visibility === "second_view_required" ? " btn-primary" : ""}`}
              disabled={!!result}
              onClick={() => {
                setVisibility("second_view_required");
                setStageIndex(spatialSequencePrefix(flowConfig).length);
              }}
            >
              Nein — es gibt verdeckte Stellen
            </button>
          </div>
        </>
      )}

      {current?.type === "projection_fill" && (
        <>
          <p>
            {gridSizeHint === "derive"
              ? "Wähle pro Ansicht die Rastergrösse, dann trage die Werte ein (0 = leer, 1 = belegt bei Vorder-/Rechtsansicht)."
              : "Trage die drei Ansichten ein (0 = leer, 1 = belegt bei Vorder-/Rechtsansicht)."}
          </p>
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
                cameraLocked={visibility === "one_view_sufficient" || Boolean(hintPreviewCamera)}
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
