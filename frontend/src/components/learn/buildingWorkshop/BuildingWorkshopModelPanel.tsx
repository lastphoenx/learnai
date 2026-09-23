"use client";

import { useEffect, useMemo, useState } from "react";
import type { HeightMatrix } from "@/lib/isoBuilding";
import type { SpatialCameraPreset } from "@/lib/spatialCoordinates";
import { clampWorkshopModelMode } from "@/lib/workshopModelUnlock";
import { BuildingThreeCanvas } from "@/components/learn/BuildingThreeCanvas";
import { BuildingHeightPlanSvg } from "@/components/learn/buildingWorkshop/BuildingHeightPlanSvg";
import type { WorkshopModelMode } from "@/components/learn/buildingWorkshop/workshopModelTypes";

export type { WorkshopModelMode };

type Props = {
  matrix: HeightMatrix;
  firstCamera: SpatialCameraPreset;
  secondCamera: SpatialCameraPreset;
  mode: WorkshopModelMode;
  onModeChange: (mode: WorkshopModelMode) => void;
  unlockedModes: WorkshopModelMode[];
  showColumnInspector?: boolean;
  cameraLocked?: boolean;
  disabled?: boolean;
};

const MODE_LABELS: Record<WorkshopModelMode, string> = {
  oblique: "1. Schrägansicht",
  second: "2. Sicht (gedreht)",
  top: "Von oben",
  heights: "Höhenplan (Hilfe)",
  occupancy: "Belegung (ohne Höhe)",
};

export function BuildingWorkshopModelPanel({
  matrix,
  firstCamera,
  secondCamera,
  mode,
  onModeChange,
  unlockedModes,
  showColumnInspector = false,
  cameraLocked = true,
  disabled = false,
}: Props) {
  const [sliceCol, setSliceCol] = useState<number | null>(null);
  const cols = matrix[0]?.length ?? 1;
  const rows = matrix.length;

  useEffect(() => {
    const clamped = clampWorkshopModelMode(mode, unlockedModes);
    if (clamped !== mode) onModeChange(clamped);
  }, [mode, unlockedModes, onModeChange]);

  const threePreset = useMemo((): SpatialCameraPreset => {
    if (mode === "second") return secondCamera;
    if (mode === "top") return "top";
    return firstCamera;
  }, [mode, firstCamera, secondCamera]);

  const show3d = mode === "oblique" || mode === "second" || mode === "top";
  const note = useMemo(() => {
    if (mode === "oblique") {
      return "Erste Schrägansicht: drehen und zoomen. Prüfe, welche Säulen sichtbar und welche verdeckt sind.";
    }
    if (mode === "second") {
      return "Zweite Schrägansicht (andere Kamera). Vergleiche mit der ersten Sicht.";
    }
    if (mode === "top") {
      return "Draufsicht: alle belegten Standorte — Höhen musst du aus den Schrägansichten erschliessen.";
    }
    if (mode === "heights") {
      return "Höhenplan (starke Hilfe): jede Zahl = Stapelhöhe. Unten = vorne (Tiefe 1), oben = hinten.";
    }
    return "Draufsicht nur Belegt/Leer (ohne Höhenzahlen). Unten = vorne (Tiefe 1).";
  }, [mode]);

  function pickMode(next: WorkshopModelMode) {
    if (disabled || !unlockedModes.includes(next)) return;
    onModeChange(next);
    setSliceCol(null);
  }

  function sliceLabel(col: number): string {
    const parts = matrix.map((row, y) => `T${y + 1}:${row[col] ?? 0}`);
    return `Spalte ${String.fromCharCode(65 + col)} — Höhen von vorne (1) nach hinten (${rows}): ${parts.join(" · ")}`;
  }

  return (
    <div className="building-workshop-model stack">
      <div className="building-workshop-stage">
        {show3d ? (
          <BuildingThreeCanvas
            matrix={matrix}
            cameraPreset={threePreset}
            cameraLocked={cameraLocked}
            showOrientationLabels={true}
            heightPx={300}
          />
        ) : (
          <BuildingHeightPlanSvg
            matrix={matrix}
            showHeights={mode === "heights"}
            title={mode === "heights" ? "Höhenplan (starke Hilfe)" : "Draufsicht — Belegung"}
          />
        )}
        {sliceCol !== null ? <div className="building-workshop-slice muted">{sliceLabel(sliceCol)}</div> : null}
      </div>
      <div className="building-workshop-model-tools" role="toolbar" aria-label="Ansichten und Hilfen">
        {(["oblique", "second", "top", "occupancy", "heights"] as WorkshopModelMode[])
          .filter((m) => unlockedModes.includes(m))
          .map((m) => (
            <button
              key={m}
              type="button"
              className={mode === m ? "active" : ""}
              disabled={disabled}
              onClick={() => pickMode(m)}
            >
              {MODE_LABELS[m]}
            </button>
          ))}
        {showColumnInspector ? (
          <>
            <span className="building-workshop-slice-label">Spalte im Schrägbild (starke Hilfe):</span>
            {Array.from({ length: cols }, (_, i) => (
              <button
                key={i}
                type="button"
                className={sliceCol === i ? "active" : ""}
                disabled={disabled}
                onClick={() => {
                  setSliceCol(i);
                  if (unlockedModes.includes("oblique")) onModeChange("oblique");
                }}
              >
                {String.fromCharCode(65 + i)}
              </button>
            ))}
          </>
        ) : null}
      </div>
      <p className="muted building-workshop-model-note">{note}</p>
    </div>
  );
}
