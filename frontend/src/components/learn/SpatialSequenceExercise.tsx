"use client";

import { useMemo, useState } from "react";
import type { TrainerSpatialSequenceConfig } from "@/lib/api";
import type { SpatialCameraPreset } from "@/lib/spatialCoordinates";
import { buildingProjections } from "@/lib/buildingProjections";
import { BuildingThreeCanvas } from "@/components/learn/BuildingThreeCanvas";
import { ProjectionFillGrids } from "@/components/learn/ProjectionFillGrids";
import { emptyProjectionDraft, type SpatialSequenceAnswer, type SpatialSequenceStage } from "@/lib/spatialSequence";

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

  const solutionOverlay = useMemo(() => (overlayHint ? buildingProjections(matrix) : null), [overlayHint, matrix]);

  const current = stages[stageIndex];
  const camera: SpatialCameraPreset =
    (current?.type === "inspect" ? (current.camera as SpatialCameraPreset) : "oblique") ?? "oblique";
  const secondCamUnlocked = hints.slice(0, unlockedHints).includes("show_second_camera");
  const cameraLocked =
    current?.type === "inspect"
      ? Boolean(current.camera_locked) && !(current.unlock_hint === "show_second_camera" && secondCamUnlocked)
      : false;

  const projectionStageIndex = stages.findIndex((s) => s.type === "projection_fill");

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

  function unlockNextHint() {
    setUnlockHints((n) => Math.min(n + 1, hints.length));
    const id = hints[unlockedHints];
    if (id === "show_solution_overlay") setOverlayHint(true);
    if (id === "show_second_camera") {
      const idx = stages.findIndex(
        (s, i) => i > stageIndex && s.type === "inspect" && s.unlock_hint === "show_second_camera",
      );
      if (idx >= 0) setStageIndex(idx);
    }
    if (id === "show_top_view") {
      const idx = stages.findIndex((s) => s.type === "inspect" && s.camera === "top");
      if (idx >= 0) setStageIndex(idx);
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
            cameraPreset={camera}
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
          />
        </>
      )}

      {hints.length > 0 && !result && (
        <div className="spatial-seq-hints">
          {unlockedHints < hints.length && (
            <button type="button" className="btn btn-sm btn-secondary" onClick={unlockNextHint}>
              Hilfe: {HINT_LABELS[hints[unlockedHints]] ?? hints[unlockedHints]}
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
