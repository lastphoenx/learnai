"use client";

import { useMemo, useState } from "react";
import type { TrainerSyntheticViewpointConfig } from "@/lib/api";
import { BuildingStandpointWorkshopShell } from "@/components/learn/buildingWorkshop/BuildingStandpointWorkshopShell";
import { BuildingWorkshopModelPanel } from "@/components/learn/buildingWorkshop/BuildingWorkshopModelPanel";
import { BuildingThreeCanvas } from "@/components/learn/BuildingThreeCanvas";
import { ViewpointPlan, viewpointCandidateLabel } from "@/components/learn/ViewpointPlan";
import {
  syntheticViewpointWorkshopModelUnlock,
  type SyntheticViewpointWorkshopPhase,
} from "@/lib/workshop/syntheticViewpointCapabilities";
import { useWorkshopFlow } from "@/lib/workshop/useWorkshopFlow";
import type { WorkshopModelMode } from "@/components/learn/buildingWorkshop/workshopModelTypes";
import { heightMatrixHasVoxels } from "@/lib/isoBuilding";

type Props = {
  config: TrainerSyntheticViewpointConfig;
  busy: boolean;
  result: { correct: boolean; expected_label?: string | null } | null;
  onSubmit: (answer: string) => void;
  onContinue: () => void;
};

export function SyntheticViewpointWorkshopExercise({ config, busy, result, onSubmit, onContinue }: Props) {
  const matrix = useMemo(() => config.height_matrix ?? [[1]], [config.height_matrix]);
  const hasBuilding = heightMatrixHasVoxels(matrix);
  const candidates = config.candidates?.length ? config.candidates : [];
  const [picked, setPicked] = useState<string | null>(null);
  const [phase, setPhase] = useState<SyntheticViewpointWorkshopPhase>("inspect");
  const unlockContext = useMemo(() => ({ phase }), [phase]);
  const locked = Boolean(result) || busy;

  const workshop = useWorkshopFlow({
    hints: [],
    initialMode: "oblique" as WorkshopModelMode,
    unlockContext,
    resolveModelUnlock: syntheticViewpointWorkshopModelUnlock,
  });

  function choose(id: string) {
    if (locked || phase !== "choose") return;
    setPicked(id);
    onSubmit(id);
  }

  if (!hasBuilding) {
    return (
      <div className="synthetic-viewpoint stack">
        <div className="learn-feedback bad" role="alert">
          <strong>Gebäudedaten fehlen</strong>
          <p className="muted" style={{ margin: "0.35rem 0 0" }}>
            Der Höhenplan ist leer oder ungültig — diese Aufgabe kann nicht bearbeitet werden.
          </p>
        </div>
      </div>
    );
  }

  const showChoice = phase === "choose";

  return (
    <BuildingStandpointWorkshopShell
      taskTitle="Standort des Betrachters"
      taskPrompt="Erkenne aus der Schrägansicht, wo der Betrachter steht — dann wähle den passenden Standpunkt."
      instruction={
        phase === "inspect"
          ? "Schritt 1: Drehe das Gebäude. Achte auf Vorne/Hinten/Links/Rechts und wo du selbst stehen müsstest."
          : "Schritt 2: Vergleiche 3D-Marker, Draufsicht-Plan und Liste — dann entscheide."
      }
      modelPanel={
        showChoice
          ? (
              <div className="stack">
                <BuildingWorkshopModelPanel
                  matrix={matrix}
                  firstCamera="oblique"
                  secondCamera="front_right"
                  mode={workshop.modelMode}
                  onModeChange={workshop.setModelMode}
                  unlockedModes={workshop.modelUnlock.unlockedModes}
                  cameraLocked={true}
                  disabled={locked}
                />
                <p className="muted building-iso-hint">
                  Oder direkt in der Szene: 👁 antippen (Marker am Gebäude mitgedreht).
                </p>
                <BuildingThreeCanvas
                  matrix={matrix}
                  showOrientationLabels={true}
                  heightPx={280}
                  viewpointCandidates={candidates}
                  selectedViewpointId={picked}
                  onViewpointPick={choose}
                  viewpointPickDisabled={locked}
                />
              </div>
            )
          : (
              <BuildingWorkshopModelPanel
                matrix={matrix}
                firstCamera="oblique"
                secondCamera="front_right"
                mode="oblique"
                onModeChange={workshop.setModelMode}
                unlockedModes={workshop.modelUnlock.unlockedModes}
                cameraLocked={true}
                disabled={locked}
              />
            )
      }
      planAside={showChoice ? <ViewpointPlan matrix={matrix} candidates={candidates} selectedId={picked} /> : null}
      choiceBlock={
        showChoice
          ? (
              <div className="viewpoint-choice-list stack" style={{ gap: "0.5rem" }}>
                {candidates.map((c) => (
                  <button
                    key={c.id}
                    type="button"
                    className="btn-secondary viewpoint-choice-btn"
                    style={{ textAlign: "left", justifyContent: "flex-start" }}
                    disabled={locked}
                    onClick={() => choose(c.id)}
                  >
                    <span className="viewpoint-choice-id">{c.id}</span>
                    <span>{viewpointCandidateLabel(c)}</span>
                  </button>
                ))}
              </div>
            )
          : undefined
      }
      actions={
        phase === "inspect" && !result
          ? (
              <button type="button" className="btn btn-secondary" onClick={() => setPhase("choose")}>
                Weiter zur Standort-Wahl
              </button>
            )
          : null
      }
      footer={
        result
          ? (
              <div className={`learn-feedback ${result.correct ? "ok" : "bad"}`}>
                {result.correct ? (
                  <strong style={{ color: "var(--accent)" }}>Richtig!</strong>
                ) : (
                  <strong style={{ color: "var(--danger)" }}>
                    Erwartet: {result.expected_label ?? "—"}
                  </strong>
                )}
                <button type="button" className="btn-primary" onClick={onContinue} disabled={busy} style={{ marginTop: "0.75rem" }}>
                  Weiter
                </button>
              </div>
            )
          : null
      }
    />
  );
}
