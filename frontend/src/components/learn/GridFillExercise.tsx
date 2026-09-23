"use client";

import { useMemo, useState } from "react";
import type { TrainerGridFillConfig } from "@/lib/api";
import { BuildingIsoPreview } from "@/components/learn/BuildingIsoPreview";

const COLOR_MAP: Record<string, string> = {
  yellow: "#e6c200",
  green: "#2d9f4e",
  purple: "#8b4bb8",
  blue: "#3b82c4",
  orange: "#e07b2d",
  empty: "transparent",
};

type Props = {
  config: TrainerGridFillConfig;
  busy: boolean;
  result: {
    correct: boolean;
    label_slots?: { id: string; correct: boolean; expected_term?: string | null; user_term?: string | null }[] | null;
  } | null;
  onSubmit: (answerJson: string) => void;
  onContinue: () => void;
};

function emptyGrid(rows: number, cols: number): (string | number | null)[][] {
  return Array.from({ length: rows }, () => Array.from({ length: cols }, () => null));
}

export function GridFillExercise({ config, busy, result, onSubmit, onContinue }: Props) {
  const { rows, cols, cell_type, palette = [] } = config;
  const [grid, setGrid] = useState<(string | number | null)[][]>(() => emptyGrid(rows, cols));
  const colorPalette = palette.length ? palette : ["yellow", "green", "purple", "blue", "orange", "empty"];

  const slotMap = useMemo(() => {
    const m = new Map<string, { correct: boolean }>();
    for (const s of result?.label_slots ?? []) {
      m.set(s.id, { correct: s.correct });
    }
    return m;
  }, [result?.label_slots]);

  function setCell(ri: number, ci: number, value: string | number | null) {
    if (result) return;
    setGrid((prev) => {
      const next = prev.map((row) => [...row]);
      next[ri][ci] = value;
      return next;
    });
  }

  function cycleColor(ri: number, ci: number) {
    const current = grid[ri][ci];
    const idx = colorPalette.indexOf(String(current ?? "empty"));
    const next = colorPalette[(idx + 1) % colorPalette.length];
    setCell(ri, ci, next === "empty" ? null : next);
  }

  const refMatrix = config.reference_height_matrix;

  return (
    <div className="grid-fill-exercise stack">
      {refMatrix && refMatrix.length > 0 && (
        <BuildingIsoPreview matrix={refMatrix} showInspector={config.validation === "derived_projection"} />
      )}
      <div
        className="grid-fill-table"
        style={{ gridTemplateColumns: `repeat(${cols}, minmax(2.5rem, 1fr))` }}
      >
        {grid.map((row, ri) =>
          row.map((cell, ci) => {
            const slot = slotMap.get(`${ri}-${ci}`);
            const isNumber = cell_type === "number";
            return (
              <div
                key={`${ri}-${ci}`}
                className={`grid-fill-cell${slot?.correct ? " slot-ok" : ""}${slot && !slot.correct ? " slot-bad" : ""}`}
              >
                {isNumber ? (
                  <input
                    type="text"
                    inputMode="numeric"
                    className="grid-fill-input"
                    value={cell === null ? "" : String(cell)}
                    disabled={busy || Boolean(result)}
                    onChange={(e) => {
                      const v = e.target.value.trim();
                      if (!v) setCell(ri, ci, null);
                      else {
                        const n = parseInt(v, 10);
                        if (!Number.isNaN(n)) setCell(ri, ci, n);
                      }
                    }}
                  />
                ) : (
                  <button
                    type="button"
                    className="grid-fill-color-btn"
                    disabled={busy || Boolean(result)}
                    style={{
                      background: COLOR_MAP[String(cell ?? "empty")] || "var(--surface-2)",
                    }}
                    aria-label={`Zelle ${ri + 1}-${ci + 1}`}
                    onClick={() => cycleColor(ri, ci)}
                  />
                )}
              </div>
            );
          }),
        )}
      </div>
      {!result ? (
        <button
          type="button"
          className="btn-primary"
          disabled={busy}
          onClick={() => onSubmit(JSON.stringify(grid))}
        >
          Prüfen
        </button>
      ) : (
        <div className={`learn-feedback ${result.correct ? "ok" : "bad"}`}>
          {result.correct ? (
            <strong style={{ color: "var(--accent)" }}>Richtig!</strong>
          ) : (
            <strong style={{ color: "var(--danger)" }}>Noch nicht — prüfe die markierten Zellen.</strong>
          )}
          <button type="button" className="btn-primary" onClick={onContinue} disabled={busy} style={{ marginTop: "0.75rem" }}>
            Weiter
          </button>
        </div>
      )}
    </div>
  );
}
