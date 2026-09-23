"use client";

import { useState } from "react";
import {
  GRID_FILL_COLOR_MAP,
  emptyGrid,
  resizeGrid,
} from "@/components/learn/gridFill/gridFillGridUtils";
import {
  initialGridFillDimensions,
  normalizeGridSizeHint,
  PROJECTION_MAX_COLS,
  PROJECTION_MAX_ROWS,
} from "@/lib/spatialGridSize";
import type { TrainerGridFillConfig } from "@/lib/api";

export function useGridFillPlanState(config: TrainerGridFillConfig) {
  const gridSizeHint = normalizeGridSizeHint(config.grid_size_hint);
  const initialDims = initialGridFillDimensions(config.rows, config.cols, config.grid_size_hint);
  const [size, setSize] = useState(initialDims);
  const [grid, setGrid] = useState<(string | number | null)[][]>(() =>
    emptyGrid(initialDims.rows, initialDims.cols),
  );
  return { gridSizeHint, size, setSize, grid, setGrid };
}

type EditorProps = {
  config: TrainerGridFillConfig;
  busy: boolean;
  locked: boolean;
  grid: (string | number | null)[][];
  setGrid: React.Dispatch<React.SetStateAction<(string | number | null)[][]>>;
  size: { rows: number; cols: number };
  setSize: React.Dispatch<React.SetStateAction<{ rows: number; cols: number }>>;
  slotMap: Map<string, { correct: boolean; expected?: string | null; user?: string | null }>;
};

export function GridFillPlanEditor({
  config,
  busy,
  locked,
  grid,
  setGrid,
  size,
  setSize,
  slotMap,
}: EditorProps) {
  const { rows: configRows, cols: configCols, cell_type, palette = [] } = config;
  const gridSizeHint = normalizeGridSizeHint(config.grid_size_hint);
  const isNumber = cell_type === "number";
  const rows = gridSizeHint === "derive" ? size.rows : configRows;
  const cols = gridSizeHint === "derive" ? size.cols : configCols;
  const colorPalette = palette.length ? palette : ["yellow", "green", "purple", "blue", "orange", "empty"];

  const sizeFeedback = slotMap.get("grid_size");
  const sizeBad = sizeFeedback && !sizeFeedback.correct;

  function setCell(ri: number, ci: number, value: string | number | null) {
    if (locked) return;
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

  function bumpSize(field: "rows" | "cols", delta: number) {
    if (locked) return;
    const max = field === "rows" ? PROJECTION_MAX_ROWS : PROJECTION_MAX_COLS;
    setSize((prev) => {
      const nextVal = Math.max(1, Math.min(max, prev[field] + delta));
      const next = { ...prev, [field]: nextVal };
      setGrid((g) => resizeGrid(g, next.rows, next.cols));
      return next;
    });
  }

  return (
    <>
      {gridSizeHint === "derive" && (
        <div
          className={`projection-size-controls${sizeBad ? " projection-fill-view--bad" : ""}`}
          role="group"
          aria-label="Rastergrösse"
        >
          <span className="muted">Raster:</span>
          <button
            type="button"
            className="btn btn-sm btn-secondary"
            disabled={busy || locked || rows <= 1}
            onClick={() => bumpSize("rows", -1)}
          >
            − Zeile
          </button>
          <span>{rows}×{cols}</span>
          <button
            type="button"
            className="btn btn-sm btn-secondary"
            disabled={busy || locked || rows >= PROJECTION_MAX_ROWS}
            onClick={() => bumpSize("rows", 1)}
          >
            + Zeile
          </button>
          <button
            type="button"
            className="btn btn-sm btn-secondary"
            disabled={busy || locked || cols <= 1}
            onClick={() => bumpSize("cols", -1)}
          >
            − Spalte
          </button>
          <button
            type="button"
            className="btn btn-sm btn-secondary"
            disabled={busy || locked || cols >= PROJECTION_MAX_COLS}
            onClick={() => bumpSize("cols", 1)}
          >
            + Spalte
          </button>
          {sizeBad && sizeFeedback ? (
            <span className="muted" style={{ color: "var(--danger)" }}>
              Erwartet {sizeFeedback.expected ?? "?"}, du hast {sizeFeedback.user ?? "?"} gewählt.
            </span>
          ) : null}
        </div>
      )}
      <div
        className="grid-fill-table"
        style={{ gridTemplateColumns: `repeat(${cols}, minmax(2.5rem, 1fr))` }}
      >
        {grid.map((row, ri) =>
          row.map((cell, ci) => {
            const slot = slotMap.get(`${ri}-${ci}`);
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
                    disabled={busy || locked}
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
                    disabled={busy || locked}
                    style={{
                      background: GRID_FILL_COLOR_MAP[String(cell ?? "empty")] || "var(--surface-2)",
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
    </>
  );
}
