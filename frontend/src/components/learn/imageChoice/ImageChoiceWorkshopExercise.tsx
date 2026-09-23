"use client";

import { useMemo, useState } from "react";
import { SourceImageCrop } from "@/components/learn/SourceImageCrop";
import { BuildingThreeCanvas } from "@/components/learn/BuildingThreeCanvas";
import { BuildingPaintWorkshopShell } from "@/components/learn/buildingWorkshop/BuildingPaintWorkshopShell";
import { sourceFileUrl, type TrainerImageChoiceConfig, type TrainerOrientationCubeConfig } from "@/lib/api";

type Props = {
  unitId: string;
  config: TrainerImageChoiceConfig;
  orientationCube: TrainerOrientationCubeConfig;
  busy: boolean;
  result: { correct: boolean; expected?: string | null } | null;
  onSubmit: (optionId: string) => void;
  onContinue: () => void;
};

type Phase = "inspect" | "choose";

export function ImageChoiceWorkshopExercise({
  unitId,
  config,
  orientationCube,
  busy,
  result,
  onSubmit,
  onContinue,
}: Props) {
  const matrix = orientationCube.height_matrix;
  const faceColors = orientationCube.colored_faces ?? {};
  const [phase, setPhase] = useState<Phase>("inspect");
  const [selected, setSelected] = useState<string | null>(null);
  const reference = config.reference;

  const displayColors = useMemo(() => {
    const out: Record<string, string> = {};
    for (const [k, v] of Object.entries(faceColors)) {
      out[k] = String(v);
    }
    return out;
  }, [faceColors]);

  function pick(id: string) {
    if (result || busy || phase !== "choose") return;
    setSelected(id);
    onSubmit(id);
  }

  return (
    <BuildingPaintWorkshopShell
      taskTitle="Farbe der sichtbaren Fläche"
      taskPrompt="Drehe den Würfel — welche Antwort zeigt die Farbe der Fläche, die du von deiner Sicht am besten siehst?"
      instruction={
        phase === "inspect"
          ? "Schritt 1: Drehe den Würfel und merke dir die sichtbare Flächenfarbe."
          : "Schritt 2: Die Ansicht ist fixiert — wähle die passende Bildoption (nicht mehr drehen)."
      }
      modelPanel={
        <BuildingThreeCanvas
          matrix={matrix}
          faceColors={displayColors}
          interactive={false}
          faceInteraction="orientable"
          showOrientationLabels={true}
          heightPx={320}
          cameraPreset="oblique"
          cameraLocked={phase === "choose"}
        />
      }
      paintBlock={
        phase === "choose"
          ? (
              <div className="image-choice-exercise stack">
                {reference?.source_id && reference.bbox && (
                  <div className="image-choice-reference">
                    <SourceImageCrop
                      url={sourceFileUrl(unitId, reference.source_id)}
                      bbox={reference.bbox}
                      alt="Aufgabenbild"
                    />
                  </div>
                )}
                <div className="image-choice-options" role="listbox" aria-label="Bildoptionen">
                  {config.options.map((opt) => {
                    const isSelected = selected === opt.id;
                    const showOk = result?.correct && isSelected;
                    const showBad = result && !result.correct && isSelected;
                    return (
                      <button
                        key={opt.id}
                        type="button"
                        role="option"
                        className={`image-choice-option${isSelected ? " selected" : ""}${showOk ? " ok" : ""}${showBad ? " bad" : ""}`}
                        disabled={busy || Boolean(result)}
                        onClick={() => pick(opt.id)}
                      >
                        <span className="image-choice-option-label">{opt.id}</span>
                        <SourceImageCrop
                          url={sourceFileUrl(unitId, opt.source_id)}
                          bbox={opt.bbox}
                          alt={`Option ${opt.id}`}
                        />
                      </button>
                    );
                  })}
                </div>
              </div>
            )
          : null
      }
      actions={
        phase === "inspect" && !result
          ? (
              <button type="button" className="btn btn-secondary" onClick={() => setPhase("choose")}>
                Weiter zur Auswahl
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
                  <>
                    <strong style={{ color: "var(--danger)" }}>Noch nicht.</strong>
                    {result.expected && (
                      <p className="muted" style={{ margin: "0.35rem 0 0" }}>
                        Richtige Antwort: {result.expected}
                      </p>
                    )}
                  </>
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
