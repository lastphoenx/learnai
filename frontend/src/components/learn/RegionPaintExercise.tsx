"use client";

import { useMemo, useState } from "react";
import type { TrainerRegionPaintConfig } from "@/lib/api";
import { BuildingThreeCanvas } from "@/components/learn/BuildingThreeCanvas";

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

export function RegionPaintExercise({ config, busy, result, onSubmit, onContinue }: Props) {
  const palette = config.palette?.length ? config.palette : ["yellow", "green", "purple", "blue", "orange"];
  const [selectedColor, setSelectedColor] = useState(palette[0] || "yellow");
  const [colors, setColors] = useState<Record<string, string>>({});

  const useThree = Boolean(config.height_matrix && config.height_matrix.length > 0);
  const matrix = config.height_matrix!;

  const slotMap = useMemo(() => {
    const m = new Map<string, boolean>();
    for (const s of result?.label_slots ?? []) {
      if (s.id) m.set(s.id, s.correct);
    }
    return m;
  }, [result?.label_slots]);

  const vw = config.view_width || 400;
  const vh = config.view_height || 280;

  function paintRegion(regionId: string) {
    if (result) return;
    setColors((prev) => ({ ...prev, [regionId]: selectedColor }));
  }

  return (
    <div className="region-paint-exercise stack">
      {config.title && <p className="muted">{config.title}</p>}
      <div className="region-paint-palette" role="toolbar" aria-label="Farben">
        {palette.map((c) => (
          <button
            key={c}
            type="button"
            className={`region-paint-swatch${selectedColor === c ? " active" : ""}`}
            style={{ background: COLOR_MAP[c] || c }}
            disabled={busy || Boolean(result)}
            aria-label={c}
            onClick={() => setSelectedColor(c)}
          />
        ))}
      </div>
      <p className="muted region-paint-hint">
        {useThree
          ? "Farbe wählen, dann die sichtbare Würfelfläche antippen (nur oben/links/rechts sind anklickbar)."
          : "Farbe wählen, dann die beschriftete Fläche im Bild antippen."}
      </p>
      {useThree ? (
        <BuildingThreeCanvas
          matrix={matrix}
          faceColors={colors}
          interactive={!result && !busy}
          onFaceClick={(id) => paintRegion(id)}
          slotCorrect={result ? slotMap : undefined}
        />
      ) : (
        <div className="region-paint-stage" style={{ minWidth: 320 }}>
          <svg viewBox={`0 0 ${vw} ${vh}`} className="region-paint-svg" role="img">
            {(config.regions || []).map((region) => {
              const pts = region.points.map(([x, y]) => `${x * vw},${y * vh}`).join(" ");
              const fill = colors[region.id] ? COLOR_MAP[colors[region.id]] || colors[region.id] : "#f8fafc";
              const slot = slotMap.get(region.id);
              return (
                <g key={region.id}>
                  <polygon
                    points={pts}
                    fill={fill}
                    stroke={slot === false ? "var(--danger)" : slot ? "var(--accent)" : "#64748b"}
                    strokeWidth={2}
                    className="region-paint-face"
                    onClick={() => paintRegion(region.id)}
                    style={{ cursor: result || busy ? "default" : "pointer" }}
                  />
                  {region.label && (
                    <text
                      x={region.points.reduce((s, p) => s + p[0], 0) / region.points.length * vw}
                      y={region.points.reduce((s, p) => s + p[1], 0) / region.points.length * vh}
                      textAnchor="middle"
                      dominantBaseline="middle"
                      fontSize={11}
                      fontWeight={700}
                      fill="#334155"
                      pointerEvents="none"
                    >
                      {region.label}
                    </text>
                  )}
                </g>
              );
            })}
          </svg>
        </div>
      )}
      {!result ? (
        <button
          type="button"
          className="btn-primary"
          disabled={busy || Object.keys(colors).length === 0}
          onClick={() => onSubmit(JSON.stringify(colors))}
        >
          Prüfen
        </button>
      ) : (
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
      )}
    </div>
  );
}
