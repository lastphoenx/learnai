"use client";

import { useMemo, useState } from "react";
import type { HeightMatrix } from "@/lib/isoBuilding";
import type { SpatialCameraPreset } from "@/lib/spatialCoordinates";
import { BuildingThreeCanvas } from "@/components/learn/BuildingThreeCanvas";
import { BuildingHeightPlanSvg } from "@/components/learn/buildingWorkshop/BuildingHeightPlanSvg";

export type WorkshopModelMode = "oblique" | "second" | "top" | "heights" | "occupancy";

type Props = {
  matrix: HeightMatrix;
  firstCamera: SpatialCameraPreset;
  secondCamera: SpatialCameraPreset;
  cameraLocked?: boolean;
  disabled?: boolean;
  onModeChange?: (mode: WorkshopModelMode) => void;
};

export function BuildingWorkshopModelPanel({
  matrix,
  firstCamera,
  secondCamera,
  cameraLocked = true,
  disabled = false,
}: Props) {
  const [mode, setMode] = useState<WorkshopModelMode>("oblique");
  const [sliceCol, setSliceCol] = useState<number | null>(null);
  const cols = matrix[0]?.length ?? 1;

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
      return "Höhenplan (starke Hilfe): jede Zahl = Stapelhöhe an diesem Platz.";
    }
    return "Draufsicht nur Belegt/Leer (ohne Höhenzahlen).";
  }, [mode]);

  function pickMode(next: WorkshopModelMode) {
    if (disabled) return;
    setMode(next);
    setSliceCol(null);
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
        {sliceCol !== null ? (
          <div className="building-workshop-slice muted">
            Spalte {String.fromCharCode(65 + sliceCol)}: Höhen von hinten (4) nach vorne (1) —{" "}
            {matrix.map((row) => row[sliceCol] ?? 0).join(" · ")}
          </div>
        ) : null}
      </div>
      <div className="building-workshop-model-tools" role="toolbar" aria-label="Ansichten und Hilfen">
        <button
          type="button"
          className={mode === "oblique" ? "active" : ""}
          disabled={disabled}
          onClick={() => pickMode("oblique")}
        >
          1. Schrägansicht
        </button>
        <button
          type="button"
          className={mode === "second" ? "active" : ""}
          disabled={disabled}
          onClick={() => pickMode("second")}
        >
          2. Sicht (gedreht)
        </button>
        <button type="button" className={mode === "top" ? "active" : ""} disabled={disabled} onClick={() => pickMode("top")}>
          Von oben
        </button>
        <button
          type="button"
          className={mode === "heights" ? "active" : ""}
          disabled={disabled}
          onClick={() => pickMode("heights")}
        >
          Höhenplan (Hilfe)
        </button>
        <button
          type="button"
          className={mode === "occupancy" ? "active" : ""}
          disabled={disabled}
          onClick={() => pickMode("occupancy")}
        >
          Belegung (ohne Höhe)
        </button>
        <span className="building-workshop-slice-label">Spalte im Schrägbild:</span>
        {Array.from({ length: cols }, (_, i) => (
          <button
            key={i}
            type="button"
            className={sliceCol === i ? "active" : ""}
            disabled={disabled}
            onClick={() => {
              setSliceCol(i);
              if (show3d) pickMode("oblique");
            }}
          >
            {String.fromCharCode(65 + i)}
          </button>
        ))}
      </div>
      <p className="muted building-workshop-model-note">{note}</p>
    </div>
  );
}
