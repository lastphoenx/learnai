"use client";

import { useMemo, useState } from "react";
import type { TrainerRegionPaintConfig } from "@/lib/api";
import { BuildingPaintWorkshopShell } from "@/components/learn/buildingWorkshop/BuildingPaintWorkshopShell";
import { BuildingThreeCanvas } from "@/components/learn/BuildingThreeCanvas";
import { RegionPaintPalette } from "@/components/learn/regionPaint/RegionPaintPalette";

const COLOR_MAP: Record<string, string> = {
  yellow: "#e6c200",
  green: "#2d9f4e",
  purple: "#8b4bb8",
  blue: "#3b82c4",
  orange: "#e07b2d",
};

type Props = {
  config: TrainerRegionPaintConfig;
  busy: boolean;
  result: {
    correct: boolean;
    label_slots?: { id: string; correct: boolean; expected_term?: string | null; user_term?: string | null }[] | null;
  } | null;
  onSubmit: (answerJson: string) => void;
  onContinue: () => void;
};

type Phase = "inspect" | "paint";

export function RegionPaintWorkshopExercise({ config, busy, result, onSubmit, onContinue }: Props) {
  const palette = config.palette?.length ? config.palette : ["yellow", "green", "purple", "blue", "orange"];
  const matrix = config.height_matrix!;
  const [phase, setPhase] = useState<Phase>("inspect");
  const [selectedColor, setSelectedColor] = useState(palette[0] || "yellow");
  const [colors, setColors] = useState<Record<string, string>>({});

  const slotMap = useMemo(() => {
    const m = new Map<string, boolean>();
    for (const s of result?.label_slots ?? []) {
      if (s.id) m.set(s.id, s.correct);
    }
    return m;
  }, [result?.label_slots]);

  const locked = Boolean(result);

  function paintRegion(regionId: string) {
    if (locked || phase !== "paint") return;
    setColors((prev) => ({ ...prev, [regionId]: selectedColor }));
  }

  return (
    <BuildingPaintWorkshopShell
      taskTitle="Flächen am Gebäude einfärben"
      taskPrompt="Drehe das Modell — nur sichtbare Flächen kannst du markieren."
      instruction={
        phase === "inspect"
          ? "Schritt 1: Untersuche das Gebäude in der Schrägansicht (drehen und zoomen)."
          : "Schritt 2: Farbe wählen, dann die sichtbare Würfelfläche antippen."
      }
      modelPanel={
        <BuildingThreeCanvas
          matrix={matrix}
          faceColors={colors}
          interactive={phase === "paint" && !locked}
          faceInteraction="orientable"
          onFaceClick={(id) => paintRegion(id)}
          slotCorrect={result ? slotMap : undefined}
          showOrientationLabels={true}
          heightPx={340}
          cameraLocked={phase === "inspect"}
        />
      }
      paintBlock={
        phase === "paint"
          ? (
              <RegionPaintPalette
                palette={palette}
                colorMap={COLOR_MAP}
                selectedColor={selectedColor}
                onSelect={setSelectedColor}
                disabled={busy || locked}
              />
            )
          : null
      }
      actions={
        <>
          {phase === "inspect" && !result && (
            <button type="button" className="btn btn-secondary" onClick={() => setPhase("paint")}>
              Weiter zum Einfärben
            </button>
          )}
          {phase === "paint" && !result && (
            <button
              type="button"
              className="btn-primary"
              disabled={busy || Object.keys(colors).length === 0}
              onClick={() => onSubmit(JSON.stringify(colors))}
            >
              Flächen prüfen
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
                  <strong style={{ color: "var(--danger)" }}>Noch nicht — prüfe die markierten Flächen.</strong>
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
