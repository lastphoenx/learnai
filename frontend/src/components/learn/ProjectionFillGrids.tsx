"use client";

import type { GridSizeHint, ViewSize } from "@/lib/spatialGridSize";
import { PROJECTION_MAX_COLS, PROJECTION_MAX_ROWS } from "@/lib/spatialGridSize";
import { projectionReviewClass } from "@/lib/projectionReviewClass";

type Grid = number[][];

type SlotFeedback = {
  id: string;
  correct: boolean;
  expected_term?: string | null;
  user_term?: string | null;
};

type Props = {
  views: { top?: Grid; front?: Grid; right?: Grid };
  editable: boolean;
  values: { top?: Grid; front?: Grid; right?: Grid };
  onChange: (next: { top?: Grid; front?: Grid; right?: Grid }) => void;
  solutionOverlay?: { top?: Grid; front?: Grid; right?: Grid } | null;
  viewCaptions?: Partial<Record<"front" | "right" | "top", string>>;
  gridSizeHint?: GridSizeHint;
  viewSizes?: Partial<Record<"front" | "right" | "top", ViewSize>>;
  onViewSizeChange?: (view: "front" | "right" | "top", size: ViewSize) => void;
  slotFeedback?: SlotFeedback[];
};

function cloneGrid(g: Grid | undefined): Grid {
  return (g ?? []).map((row) => [...row]);
}

function isOccupied(view: "front" | "right" | "top", value: number): boolean {
  return (value ?? 0) > 0;
}

function cellsEquivalent(
  view: "front" | "right" | "top",
  a: number | undefined,
  b: number | undefined,
): boolean {
  if (view === "top") {
    return isOccupied(view, a ?? 0) === isOccupied(view, b ?? 0);
  }
  return (a ?? 0) === (b ?? 0);
}

function SizeControls({
  size,
  disabled,
  onChange,
}: {
  size: ViewSize;
  disabled: boolean;
  onChange: (next: ViewSize) => void;
}) {
  function bump(field: "rows" | "cols", delta: number) {
    const max = field === "rows" ? PROJECTION_MAX_ROWS : PROJECTION_MAX_COLS;
    const next = Math.max(1, Math.min(max, size[field] + delta));
    onChange({ ...size, [field]: next });
  }

  return (
    <div className="projection-size-controls" role="group" aria-label="Rastergrösse">
      <span className="muted">Raster:</span>
      <button type="button" className="btn btn-sm btn-secondary" disabled={disabled || size.rows <= 1} onClick={() => bump("rows", -1)}>
        − Zeile
      </button>
      <span>{size.rows}×{size.cols}</span>
      <button
        type="button"
        className="btn btn-sm btn-secondary"
        disabled={disabled || size.rows >= PROJECTION_MAX_ROWS}
        onClick={() => bump("rows", 1)}
      >
        + Zeile
      </button>
      <button type="button" className="btn btn-sm btn-secondary" disabled={disabled || size.cols <= 1} onClick={() => bump("cols", -1)}>
        − Spalte
      </button>
      <button
        type="button"
        className="btn btn-sm btn-secondary"
        disabled={disabled || size.cols >= PROJECTION_MAX_COLS}
        onClick={() => bump("cols", 1)}
      >
        + Spalte
      </button>
    </div>
  );
}

function ViewBlock({
  viewKey,
  title,
  caption,
  grid,
  editable,
  solution,
  onToggle,
  gridSizeHint,
  viewSize,
  onViewSizeChange,
  sizeFeedback,
  contentFeedback,
}: {
  viewKey: "front" | "right" | "top";
  title: string;
  caption?: string;
  grid?: Grid;
  editable: boolean;
  solution?: Grid;
  onToggle: (ri: number, ci: number) => void;
  gridSizeHint: GridSizeHint;
  viewSize?: ViewSize;
  onViewSizeChange?: (view: "front" | "right" | "top", size: ViewSize) => void;
  sizeFeedback?: SlotFeedback;
  contentFeedback?: SlotFeedback;
}) {
  if (!grid?.length) return null;
  const cols = grid[0]?.length ?? 0;
  const sizeBad = sizeFeedback && !sizeFeedback.correct;
  const contentBad = contentFeedback && !contentFeedback.correct;
  return (
    <div className={`projection-fill-view stack${sizeBad || contentBad ? " projection-fill-view--bad" : ""}`}>
      <strong>{title}</strong>
      {caption ? <p className="muted projection-fill-caption">{caption}</p> : null}
      {gridSizeHint === "derive" && viewSize && onViewSizeChange ? (
        <SizeControls
          size={viewSize}
          disabled={!editable}
          onChange={(next) => onViewSizeChange(viewKey, next)}
        />
      ) : null}
      {sizeBad ? (
        <p className="projection-size-feedback bad">
          Rastergrösse: dein {sizeFeedback?.user_term ?? "?"} — erwartet {sizeFeedback?.expected_term ?? "?"}
        </p>
      ) : null}
      <p className="muted projection-toggle-hint">Tippe ein Feld, um es zu markieren oder zu leeren.</p>
      <div
        className="grid-fill-table projection-fill-table"
        style={{ gridTemplateColumns: `repeat(${cols}, minmax(2.25rem, 1fr))` }}
      >
        {grid.map((row, ri) =>
          row.map((cell, ci) => {
            const sol = solution?.[ri]?.[ci];
            const userFilled = isOccupied(viewKey, cell);
            const expectedFilled =
              solution && sol !== undefined ? isOccupied(viewKey, sol) : false;
            const review =
              solution && sol !== undefined
                ? projectionReviewClass(userFilled, expectedFilled)
                : "";
            const reviewClass = review ? ` ${review}` : "";
            return (
              <div
                key={`${ri}-${ci}`}
                className={`grid-fill-cell projection-toggle-cell${userFilled ? " projection-toggle-cell--on" : ""}${reviewClass}${contentBad ? " slot-bad" : ""}`}
              >
                {editable ? (
                  <button
                    type="button"
                    className="projection-toggle-btn"
                    aria-pressed={userFilled}
                    aria-label={`Zeile ${ri + 1}, Spalte ${ci + 1}${userFilled ? ", markiert" : ", leer"}`}
                    onClick={() => onToggle(ri, ci)}
                  />
                ) : (
                  <span className="projection-toggle-readonly" aria-hidden={!userFilled}>{userFilled ? "■" : ""}</span>
                )}
              </div>
            );
          }),
        )}
      </div>
    </div>
  );
}

export function ProjectionFillGrids({
  views,
  editable,
  values,
  onChange,
  solutionOverlay,
  viewCaptions,
  gridSizeHint = "given",
  viewSizes,
  onViewSizeChange,
  slotFeedback,
}: Props) {
  const keys = (["front", "right", "top"] as const).filter((k) => views[k]?.length);
  const feedbackById = new Map((slotFeedback ?? []).map((s) => [s.id, s]));

  function toggleCell(key: "top" | "front" | "right", ri: number, ci: number) {
    const base = cloneGrid(values[key] ?? views[key]);
    while (base.length <= ri) base.push([]);
    while (base[ri].length <= ci) base[ri].push(0);
    const cur = base[ri][ci] ?? 0;
    base[ri][ci] = cur > 0 ? 0 : 1;
    onChange({ ...values, [key]: base });
  }

  const titles = { front: "Vorderansicht", right: "Rechtsansicht", top: "Aufsicht" };

  return (
    <div className="projection-fill-grids stack">
      {keys.map((k) => (
        <ViewBlock
          key={k}
          viewKey={k}
          title={titles[k]}
          caption={viewCaptions?.[k]}
          grid={values[k] ?? views[k]}
          editable={editable}
          solution={solutionOverlay?.[k]}
          onToggle={(ri, ci) => toggleCell(k, ri, ci)}
          gridSizeHint={gridSizeHint}
          viewSize={viewSizes?.[k]}
          onViewSizeChange={onViewSizeChange}
          sizeFeedback={feedbackById.get(`${k}_size`)}
          contentFeedback={feedbackById.get(k)}
        />
      ))}
    </div>
  );
}
