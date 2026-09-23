"use client";

import { useMemo } from "react";
import { type HeightMatrix, classifyColumnVisibility } from "@/lib/isoBuilding";
import { BuildingThreeCanvas } from "@/components/learn/BuildingThreeCanvas";

type Props = {
  matrix: HeightMatrix;
  showInspector?: boolean;
  showCameraToggle?: boolean;
};

/** 3D-Vorschau (Three.js) — Drehen/Zoomen statt fester Schrägansicht. */
export function BuildingIsoPreview({ matrix }: Props) {
  const visibility = useMemo(() => classifyColumnVisibility(matrix), [matrix]);

  return (
    <div className="building-iso-preview stack">
      {!visibility.allReadable && (
        <p className="muted building-iso-hint">
          Einige Spalten sind aus einer festen Richtung verdeckt — Gebäude drehen (Finger/Maus), bis alles sichtbar ist.
        </p>
      )}
      <p className="muted building-iso-hint">Drehen: ziehen · Zoomen: zwei Finger oder Mausrad</p>
      <BuildingThreeCanvas matrix={matrix} interactive={false} />
    </div>
  );
}
