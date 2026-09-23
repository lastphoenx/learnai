"use client";

import { useMemo, useState } from "react";
import { type HeightMatrix, classifyColumnVisibility } from "@/lib/isoBuilding";
import { BuildingThreeCanvas } from "@/components/learn/BuildingThreeCanvas";
import type { SpatialCameraPreset } from "@/lib/spatialCoordinates";

type Props = {
  matrix: HeightMatrix;
  showInspector?: boolean;
  showCameraToggle?: boolean;
  showOrientationLabels?: boolean;
};

const CAMERA_OPTIONS: { id: SpatialCameraPreset; label: string }[] = [
  { id: "oblique", label: "Schräg" },
  { id: "front", label: "Vorne" },
  { id: "right", label: "Rechts" },
  { id: "top", label: "Oben" },
];

/** 3D-Vorschau (Three.js) — Drehen/Zoomen statt fester Schrägansicht. */
export function BuildingIsoPreview({
  matrix,
  showOrientationLabels = true,
  showCameraToggle = false,
}: Props) {
  const visibility = useMemo(() => classifyColumnVisibility(matrix), [matrix]);
  const [cameraPreset, setCameraPreset] = useState<SpatialCameraPreset>("oblique");

  return (
    <div className="building-iso-preview stack">
      {!visibility.allReadable && (
        <p className="muted building-iso-hint">
          Einige Spalten sind aus einer festen Richtung verdeckt — Gebäude drehen (Finger/Maus), bis alles sichtbar ist.
        </p>
      )}
      {showCameraToggle && (
        <div className="building-camera-toggle" role="group" aria-label="Kamera">
          {CAMERA_OPTIONS.map((opt) => (
            <button
              key={opt.id}
              type="button"
              className={`btn btn-sm${cameraPreset === opt.id ? " btn-primary" : ""}`}
              onClick={() => setCameraPreset(opt.id)}
            >
              {opt.label}
            </button>
          ))}
        </div>
      )}
      <p className="muted building-iso-hint">Drehen: ziehen · Zoomen: zwei Finger oder Mausrad</p>
      <BuildingThreeCanvas
        matrix={matrix}
        interactive={false}
        showOrientationLabels={showOrientationLabels}
        cameraPreset={cameraPreset}
      />
    </div>
  );
}
