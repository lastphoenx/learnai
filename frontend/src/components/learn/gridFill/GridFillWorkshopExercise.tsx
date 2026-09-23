"use client";

import { useMemo, useState } from "react";
import type { TrainerGridFillConfig } from "@/lib/api";
import { BuildingPlanWorkshopShell } from "@/components/learn/buildingWorkshop/BuildingPlanWorkshopShell";
import { BuildingWorkshopModelPanel } from "@/components/learn/buildingWorkshop/BuildingWorkshopModelPanel";
import {
  GridFillPlanEditor,
  useGridFillPlanState,
} from "@/components/learn/gridFill/GridFillPlanEditor";
import {
  gridFillWorkshopModelUnlock,
  type GridFillWorkshopPhase,
} from "@/lib/workshop/gridFillCapabilities";
import { useWorkshopFlow } from "@/lib/workshop/useWorkshopFlow";
import type { WorkshopModelMode } from "@/components/learn/buildingWorkshop/workshopModelTypes";

type Props = {
  config: TrainerGridFillConfig;
  busy: boolean;
  result: {
    correct: boolean;
    label_slots?: { id: string; correct: boolean; expected_term?: string | null; user_term?: string | null }[] | null;
  } | null;
  onSubmit: (answerJson: string) => void;
  onContinue: () => void;
};

export function GridFillWorkshopExercise({ config, busy, result, onSubmit, onContinue }: Props) {
  const matrix = config.reference_height_matrix!;
  const [phase, setPhase] = useState<GridFillWorkshopPhase>("inspect");
  const unlockContext = useMemo(() => ({ phase }), [phase]);

  const workshop = useWorkshopFlow({
    hints: [],
    initialMode: "oblique" as WorkshopModelMode,
    unlockContext,
    resolveModelUnlock: gridFillWorkshopModelUnlock,
  });

  const { size, setSize, grid, setGrid } = useGridFillPlanState(config);

  const slotMap = useMemo(() => {
    const m = new Map<string, { correct: boolean; expected?: string | null; user?: string | null }>();
    for (const s of result?.label_slots ?? []) {
      m.set(s.id, {
        correct: s.correct,
        expected: s.expected_term,
        user: s.user_term,
      });
    }
    return m;
  }, [result?.label_slots]);

  const sizeFeedback = slotMap.get("grid_size");
  const sizeBad = sizeFeedback && !sizeFeedback.correct;
  const locked = Boolean(result);

  return (
    <BuildingPlanWorkshopShell
      taskTitle="Bauplan aus der Schrägansicht"
      taskPrompt="Untersuche das Gebäude, dann trage die Höhen in den Plan ein."
      instruction={
        phase === "inspect"
          ? "Schritt 1: Drehe und zoome in der Schrägansicht — erkenne Stapelhöhen und Tiefe (vorne/hinten)."
          : "Schritt 2: Trage die Zahlen in den Höhenplan ein. Optional: Draufsicht als Hilfe."
      }
      modelPanel={
        <BuildingWorkshopModelPanel
          matrix={matrix}
          firstCamera="oblique"
          secondCamera="oblique_left"
          mode={workshop.modelMode}
          onModeChange={workshop.setModelMode}
          unlockedModes={workshop.modelUnlock.unlockedModes}
          cameraLocked={true}
          disabled={locked}
        />
      }
      planBlock={
        phase === "plan"
          ? (
              <GridFillPlanEditor
                config={config}
                busy={busy}
                locked={locked}
                grid={grid}
                setGrid={setGrid}
                size={size}
                setSize={setSize}
                slotMap={slotMap}
              />
            )
          : (
              <p className="muted">Nach dem Untersuchen öffnet sich der Höhenplan.</p>
            )
      }
      actions={
        <>
          {phase === "inspect" && !result && (
            <button type="button" className="btn btn-secondary" onClick={() => setPhase("plan")}>
              Weiter zum Höhenplan
            </button>
          )}
          {phase === "plan" && !result && (
            <button
              type="button"
              className="btn-primary"
              disabled={busy}
              onClick={() => onSubmit(JSON.stringify(grid))}
            >
              Bauplan prüfen
            </button>
          )}
        </>
      }
      footer={
        result
          ? (
              <div className={`learn-feedback ${result.correct ? "ok" : "bad"}`}>
                {result.correct ? (
                  <strong style={{ color: "var(--accent)" }}>Richtig!</strong>
                ) : (
                  <strong style={{ color: "var(--danger)" }}>
                    {sizeBad ? "Rastergrösse oder markierte Zellen prüfen." : "Noch nicht — prüfe die markierten Zellen."}
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
