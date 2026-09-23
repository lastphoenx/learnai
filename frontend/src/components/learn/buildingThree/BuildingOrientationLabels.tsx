"use client";

import type { CSSProperties } from "react";
import { Html } from "@react-three/drei";
import type { HeightMatrix } from "@/lib/isoBuilding";

const GAP = 1.02;

type Props = {
  matrix: HeightMatrix;
};

/**
 * Richtungsbeschriftung am Gebäude (mitdrehend mit dem Modell, nicht mit der Kamera).
 * Entspricht backend building_projections: Vorne = Blick von niedrigem y (Zeile 0) nach innen.
 */
export function BuildingOrientationLabels({ matrix }: Props) {
  const cols = matrix[0]?.length ?? 1;
  const rows = matrix.length;
  const w = (cols - 1) * GAP;
  const d = (rows - 1) * GAP;
  const cx = w / 2;
  const cz = d / 2;
  const pad = 1.35;

  const labelStyle: CSSProperties = {
    fontSize: "0.72rem",
    fontWeight: 800,
    color: "#10263f",
    background: "rgba(255,255,255,0.92)",
    padding: "2px 8px",
    borderRadius: 8,
    border: "1.5px solid #c5d0dc",
    whiteSpace: "nowrap",
    pointerEvents: "none",
    userSelect: "none",
  };

  return (
    <>
      <Html position={[cx, 0.05, -pad]} center style={{ pointerEvents: "none" }}>
        <span style={labelStyle}>Vorne ↓</span>
      </Html>
      <Html position={[cx, 0.05, d + pad]} center style={{ pointerEvents: "none" }}>
        <span style={labelStyle}>Hinten ↑</span>
      </Html>
      <Html position={[-pad, 0.05, cz]} center style={{ pointerEvents: "none" }}>
        <span style={labelStyle}>Links</span>
      </Html>
      <Html position={[w + pad, 0.05, cz]} center style={{ pointerEvents: "none" }}>
        <span style={labelStyle}>Rechts</span>
      </Html>
    </>
  );
}
