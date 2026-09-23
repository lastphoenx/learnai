"use client";

import type { HeightMatrix } from "@/lib/isoBuilding";
import { SPATIAL_COORDINATE_SYSTEM } from "@/lib/spatialCoordinates";

type Props = {
  matrix: HeightMatrix;
  showHeights?: boolean;
  title?: string;
};

/** Zeile 0 = vorne — im Plan unten darstellen (wie Betrachter-Guide). */
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
          const displayRow = rows - 1 - y;
          const px = ox + x * cell;
          const py = oy + displayRow * cell;
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
          y={oy - 8}
          textAnchor="middle"
          fontSize="12"
          fontWeight="900"
          fill="#d9474b"
        >
          {String.fromCharCode(65 + x)}
        </text>
      ))}
      {Array.from({ length: rows }, (_, y) => {
        const displayRow = rows - 1 - y;
        return (
          <text
            key={`r${y}`}
            x={ox - 16}
            y={oy + displayRow * cell + cell / 2 + 4}
            textAnchor="middle"
            fontSize="12"
            fontWeight="900"
            fill="#3c76e8"
          >
            {y + 1}
          </text>
        );
      })}
      <text x={w / 2} y={oy + rows * cell + 22} textAnchor="middle" fontSize="12" fontWeight="800" fill="#d9474b">
        ↓ VORNE — Tiefe 1 ({SPATIAL_COORDINATE_SYSTEM.frontRow + 1})
      </text>
    </svg>
  );
}
