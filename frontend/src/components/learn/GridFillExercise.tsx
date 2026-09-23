"use client";

import { useMemo, useState } from "react";
import type { TrainerGridFillConfig } from "@/lib/api";
import { BuildingIsoPreview } from "@/components/learn/BuildingIsoPreview";
import {
  initialGridFillDimensions,
  normalizeGridSizeHint,
  PROJECTION_MAX_COLS,
  PROJECTION_MAX_ROWS,
} from "@/lib/spatialGridSize";

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

function resizeGrid(
  prev: (string | number | null)[][],
  rows: number,
  cols: number,
): (string | number | null)[][] {
  const next = emptyGrid(rows, cols);
  for (let ri = 0; ri < rows; ri++) {
    for (let ci = 0; ci < cols; ci++) {
      if (ri < prev.length && ci < (prev[ri]?.length ?? 0)) {
        next[ri][ci] = prev[ri][ci];
      }
    }
  }
  return next;
}

export function GridFillExercise({ config, busy, result, onSubmit, onContinue }: Props) {
  const { rows: configRows, cols: configCols, cell_type, palette = [] } = config;
  const gridSizeHint = normalizeGridSizeHint(config.grid_size_hint);
  const isNumber = cell_type === "number";
  const initialDims = initialGridFillDimensions(configRows, configCols, config.grid_size_hint);
  const [size, setSize] = useState(initialDims);
  const rows = gridSizeHint === "derive" ? size.rows : configRows;
  const cols = gridSizeHint === "derive" ? size.cols : configCols;
  const [grid, setGrid] = useState<(string | number | null)[][]>(() =>
    emptyGrid(initialDims.rows, initialDims.cols),
  );
  const colorPalette = palette.length ? palette : ["yellow", "green", "purple", "blue", "orange", "empty"];

  const slotMap = useMemo(() => {
    const m = new Map<string, { correct: boolean; expected?: string | null; user?: string | null }>();
    for (const s of result?.label_slots ?? []) {
      m.set(s.id, {
        correct: s.correct,
        expected: s.expected_term,
        user: s.user_term,
      });
    }
    return m;
  }, [result?.label_slots]);

  const sizeFeedback = slotMap.get("grid_size");
  const sizeBad = sizeFeedback && !sizeFeedback.correct;

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

  function bumpSize(field: "rows" | "cols", delta: number) {
    if (result) return;
    const max = field === "rows" ? PROJECTION_MAX_ROWS : PROJECTION_MAX_COLS;
    setSize((prev) => {
      const nextVal = Math.max(1, Math.min(max, prev[field] + delta));
      const next = { ...prev, [field]: nextVal };
      setGrid((g) => resizeGrid(g, next.rows, next.cols));
      return next;
    });
  }

  const refMatrix = config.reference_height_matrix;
  const isDerived = config.validation === "derived_projection";

  return (
    <div className="grid-fill-exercise stack">
      {gridSizeHint === "derive" ? (
        <p className="muted grid-fill-legend">
          <strong>Höhenplan:</strong> Wähle zuerst die passende Rastergrösse (Zeilen × Spalten), dann trage die Werte ein.
          Zeile 1 = <em>vorne</em>, letzte Zeile = <em>hinten</em>; Spalte 1 = <em>links</em>, letzte Spalte = <em>rechts</em>.
        </p>
      ) : (
        <p className="muted grid-fill-legend">
          <strong>Höhenplan:</strong> {rows} Zeile{rows === 1 ? "" : "n"} × {cols} Spalte{cols === 1 ? "" : "n"}.
          Zeile 1 = <em>vorne</em>, letzte Zeile = <em>hinten</em>; Spalte 1 = <em>links</em>, letzte Spalte = <em>rechts</em>.
          {isNumber ? " Jede Zelle = Anzahl übereinander gestapelter Würfel an dieser Stelle." : " Tippe Zellen zum Einfärben."}
        </p>
      )}
      {refMatrix && refMatrix.length > 0 && (
        <>
          <p className="muted">
            {isDerived
              ? "So sieht das Zielgebäude aus — trage die passenden Höhen in den Plan unten ein."
              : "Vorgabe-Gebäude (Orientierung: Vorne/Hinten/Links/Rechts am Modell)."}
          </p>
          <BuildingIsoPreview matrix={refMatrix} showOrientationLabels={true} />
        </>
      )}
      {!refMatrix?.length && isNumber && (
        <p className="muted">
          Trage die fehlenden Zahlen ein. Wenn im Auftrag ein Bild fehlt: Einheit neu aufbereiten oder Didaktik prüfen.
        </p>
      )}
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
            disabled={busy || Boolean(result) || rows <= 1}
            onClick={() => bumpSize("rows", -1)}
          >
            − Zeile
          </button>
          <span>{rows}×{cols}</span>
          <button
            type="button"
            className="btn btn-sm btn-secondary"
            disabled={busy || Boolean(result) || rows >= PROJECTION_MAX_ROWS}
            onClick={() => bumpSize("rows", 1)}
          >
            + Zeile
          </button>
          <button
            type="button"
            className="btn btn-sm btn-secondary"
            disabled={busy || Boolean(result) || cols <= 1}
            onClick={() => bumpSize("cols", -1)}
          >
            − Spalte
          </button>
          <button
            type="button"
            className="btn btn-sm btn-secondary"
            disabled={busy || Boolean(result) || cols >= PROJECTION_MAX_COLS}
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
            <strong style={{ color: "var(--danger)" }}>
              {sizeBad ? "Rastergrösse oder markierte Zellen prüfen." : "Noch nicht — prüfe die markierten Zellen."}
            </strong>
          )}
          <button type="button" className="btn-primary" onClick={onContinue} disabled={busy} style={{ marginTop: "0.75rem" }}>
            Weiter
          </button>
        </div>
      )}
    </div>
  );
}
