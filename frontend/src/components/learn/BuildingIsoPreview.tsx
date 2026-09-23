"use client";

import { useMemo, useState } from "react";
import {
  type HeightMatrix,
  type IsoCamera,
  buildColumnInspector,
  buildIsoPreviewFaces,
  classifyColumnVisibility,
} from "@/lib/isoBuilding";

type Props = {
  matrix: HeightMatrix;
  showInspector?: boolean;
  showCameraToggle?: boolean;
};

export function BuildingIsoPreview({ matrix, showInspector = true, showCameraToggle = true }: Props) {
  const [camera, setCamera] = useState<IsoCamera>("default");
  const [activeCol, setActiveCol] = useState<number | null>(null);

  const visibility = useMemo(() => classifyColumnVisibility(matrix), [matrix]);
  const faces = useMemo(() => buildIsoPreviewFaces(matrix, camera), [matrix, camera]);
  const inspector = activeCol !== null ? buildColumnInspector(matrix, activeCol, camera) : null;

  const xs = faces.flatMap((f) => f.points.map((p) => p[0]));
  const ys = faces.flatMap((f) => f.points.map((p) => p[1]));
  const minX = Math.min(...xs, 0);
  const maxX = Math.max(...xs, 400);
  const minY = Math.min(...ys, 0);
  const maxY = Math.max(...ys, 300);
  const pad = 20;

  return (
    <div className="building-iso-preview stack">
      {!visibility.allReadable && (
        <p className="muted building-iso-hint">
          Mindestens eine Spalte ist in der Schrägansicht verdeckt — «Rückansicht» nutzen oder Spalten-Inspektor.
        </p>
      )}
      <div className="building-iso-toolbar">
        {showCameraToggle && (
          <button
            type="button"
            className="btn-secondary btn-sm"
            onClick={() => setCamera((c) => (c === "default" ? "back" : "default"))}
          >
            {camera === "default" ? "Rückansicht" : "Schrägansicht"}
          </button>
        )}
        {showInspector &&
          visibility.columns.map((col) => (
            <button
              key={col.col}
              type="button"
              className={`btn-secondary btn-sm${activeCol === col.col ? " active" : ""}`}
              onClick={() => setActiveCol((c) => (c === col.col ? null : col.col))}
            >
              Spalte {col.label}
              {!col.readable ? " ⚠" : ""}
            </button>
          ))}
      </div>
      <svg viewBox={`${minX - pad} ${minY - pad} ${maxX - minX + 2 * pad} ${maxY - minY + 2 * pad}`} className="building-iso-svg" role="img">
        {faces.map((f, i) => (
          <polygon key={i} points={f.points.map(([x, y]) => `${x},${y}`).join(" ")} fill={f.fill} stroke="#475569" strokeWidth={1} />
        ))}
        {inspector && (
          <>
            <polyline
              points={inspector.guidePath.map(([x, y]) => `${x},${y}`).join(" ")}
              fill="none"
              stroke="var(--accent)"
              strokeWidth={2}
              strokeDasharray="6 4"
            />
            {inspector.markers.map((m) => (
              <g key={m.depth}>
                <circle cx={m.x} cy={m.y} r={10} fill={m.isCritical ? "var(--accent)" : "#fff"} stroke="#334155" strokeWidth={1.5} />
                <text x={m.x} y={m.y + 4} textAnchor="middle" fontSize={11} fill={m.isCritical ? "#fff" : "#0f172a"}>
                  {m.depth}
                </text>
                {m.isCritical && (
                  <line x1={m.x} y1={m.y + 12} x2={m.x} y2={m.y + 28} stroke="var(--accent)" strokeWidth={2} strokeDasharray="3 2" />
                )}
              </g>
            ))}
          </>
        )}
      </svg>
      {inspector && (
        <p className="muted building-iso-breakdown">
          Spalte {inspector.colLabel}: {inspector.breakdown} → höchste Säule: {inspector.maxHeight} (massgeblich: Tiefe{" "}
          {inspector.criticalDepth})
        </p>
      )}
    </div>
  );
}
