"use client";

import type { CSSProperties } from "react";
import type { HeightMatrix } from "@/lib/isoBuilding";
import { resolveViewpointNorm, type ViewpointCandidateLike } from "@/lib/viewpointWorld";

export type ViewpointCandidate = ViewpointCandidateLike;

type Props = {
  matrix: HeightMatrix;
  candidates: ViewpointCandidate[];
  selectedId?: string | null;
};

export function ViewpointPlan({ matrix, candidates, selectedId }: Props) {
  const rows = matrix.length;
  const cols = matrix[0]?.length ?? 1;
  const maxH = Math.max(1, ...matrix.flat());

  const labelStyle: CSSProperties = {
    fontSize: 10,
    fontWeight: 800,
    fill: "#10263f",
  };

  return (
    <div className="viewpoint-plan-wrap">
      <p className="muted viewpoint-plan-caption">Draufsicht — Standpunkte am Plan (👁 = Betrachter)</p>
      <svg viewBox="0 0 100 100" className="viewpoint-plan-svg" role="img" aria-label="Bauplan von oben mit Standpunkten">
        <rect x={8} y={8} width={84} height={84} rx={6} fill="#f1f5f9" stroke="#94a3b8" strokeWidth={1.2} />
        {matrix.map((row, ri) =>
          row.map((h, ci) => {
            const cellW = 84 / cols;
            const cellH = 84 / rows;
            const x = 8 + ci * cellW;
            const y = 8 + ri * cellH;
            const intensity = h <= 0 ? 0.15 : 0.25 + (h / maxH) * 0.45;
            return (
              <rect
                key={`${ri}-${ci}`}
                x={x + 1}
                y={y + 1}
                width={cellW - 2}
                height={cellH - 2}
                rx={2}
                fill={`rgba(60, 118, 232, ${intensity})`}
                stroke="#64748b"
                strokeWidth={0.6}
              />
            );
          }),
        )}
        <text x={50} y={5.5} textAnchor="middle" style={labelStyle} fontSize={7}>
          Hinten
        </text>
        <text x={50} y={99} textAnchor="middle" style={labelStyle} fontSize={7}>
          Vorne
        </text>
        <text x={3} y={52} textAnchor="start" style={labelStyle} fontSize={7}>
          L
        </text>
        <text x={97} y={52} textAnchor="end" style={labelStyle} fontSize={7}>
          R
        </text>
        {candidates.map((c) => {
          const [nx, ny] = resolveViewpointNorm(c);
          const px = 8 + nx * 84;
          const py = 8 + ny * 84;
          const active = selectedId === c.id;
          return (
            <g key={c.id}>
              <circle cx={px} cy={py} r={active ? 5.5 : 4.5} fill={active ? "#159b83" : "#3c76e8"} stroke="#fff" strokeWidth={1.2} />
              <text x={px} y={py + 0.5} textAnchor="middle" dominantBaseline="middle" fill="#fff" fontSize={5.5} fontWeight={900}>
                👁
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}

export function viewpointCandidateLabel(c: ViewpointCandidate): string {
  const label = (c.label || "").trim();
  if (label.length >= 3) return label;
  const fallbacks: Record<string, string> = {
    A: "Vorne (unterhalb des Plans)",
    B: "Rechts am Plan",
    C: "Hinten (oberhalb des Plans)",
    D: "Links am Plan",
  };
  return fallbacks[c.id] || `Standpunkt ${c.id}`;
}
