"use client";

import type { HeightMatrix } from "@/lib/isoBuilding";

type Props = {
  matrix: HeightMatrix;
  showHeights?: boolean;
  title?: string;
};

export function BuildingHeightPlanSvg({ matrix, showHeights = true, title }: Props) {
  const rows = matrix.length;
  const cols = matrix[0]?.length ?? 1;
  const cell = 48;
  const ox = 80;
  const oy = 36;
  const w = ox + cols * cell + 40;
  const h = oy + rows * cell + 56;

  return (
    <svg viewBox={`0 0 ${w} ${h}`} className="building-height-plan-svg" role="img">
      <text x={w / 2} y="22" textAnchor="middle" fontSize="14" fontWeight="800" fill="#10263f">
        {title ?? (showHeights ? "Höhenplan (Hilfe)" : "Draufsicht — Standorte")}
      </text>
      {matrix.map((row, y) =>
        row.map((v, x) => {
          const px = ox + x * cell;
          const py = oy + y * cell;
          return (
            <g key={`${x}-${y}`}>
              <rect
                x={px}
                y={py}
                width={cell}
                height={cell}
                rx={5}
                fill={v > 0 ? "#dcecff" : "#fff"}
                stroke={v > 0 ? "#48617c" : "#b8c7d7"}
                strokeWidth={2}
              />
              {showHeights ? (
                <text
                  x={px + cell / 2}
                  y={py + cell / 2 + 6}
                  textAnchor="middle"
                  fontSize="18"
                  fontWeight="900"
                  fill={v > 0 ? "#10263f" : "#9aa8b7"}
                >
                  {v}
                </text>
              ) : null}
            </g>
          );
        }),
      )}
      {Array.from({ length: cols }, (_, x) => (
        <text
          key={`c${x}`}
          x={ox + x * cell + cell / 2}
          y={oy + rows * cell + 22}
          textAnchor="middle"
          fontSize="12"
          fontWeight="900"
          fill="#d9474b"
        >
          {String.fromCharCode(65 + x)}
        </text>
      ))}
      {Array.from({ length: rows }, (_, y) => (
        <text
          key={`r${y}`}
          x={ox - 16}
          y={oy + y * cell + cell / 2 + 4}
          textAnchor="middle"
          fontSize="12"
          fontWeight="900"
          fill="#3c76e8"
        >
          {y + 1}
        </text>
      ))}
    </svg>
  );
}
