"use client";

type Grid = number[][];

type Props = {
  views: { top?: Grid; front?: Grid; right?: Grid };
  editable: boolean;
  values: { top?: Grid; front?: Grid; right?: Grid };
  onChange: (next: { top?: Grid; front?: Grid; right?: Grid }) => void;
  solutionOverlay?: { top?: Grid; front?: Grid; right?: Grid } | null;
};

function cloneGrid(g: Grid | undefined): Grid {
  return (g ?? []).map((row) => [...row]);
}

function setCell(grid: Grid, ri: number, ci: number, v: string) {
  const n = v.trim() === "" ? 0 : Number(v);
  if (!Number.isFinite(n)) return;
  while (grid.length <= ri) grid.push([]);
  while (grid[ri].length <= ci) grid[ri].push(0);
  grid[ri][ci] = n;
}

function ViewBlock({
  title,
  grid,
  editable,
  solution,
  onCell,
}: {
  title: string;
  grid?: Grid;
  editable: boolean;
  solution?: Grid;
  onCell: (ri: number, ci: number, v: string) => void;
}) {
  if (!grid?.length) return null;
  const cols = grid[0]?.length ?? 0;
  return (
    <div className="projection-fill-view stack">
      <strong>{title}</strong>
      <div
        className="grid-fill-table projection-fill-table"
        style={{ gridTemplateColumns: `repeat(${cols}, minmax(1.5rem, 1fr))` }}
      >
        {grid.map((row, ri) =>
          row.map((cell, ci) => {
            const sol = solution?.[ri]?.[ci];
            const showSol = solution && sol !== undefined && sol !== cell;
            return (
              <div
                key={`${ri}-${ci}`}
                className={`grid-fill-cell${showSol ? " projection-solution-hint" : ""}`}
              >
                {editable ? (
                  <input
                    type="text"
                    className="grid-fill-input"
                    value={cell === 0 && !showSol ? "" : String(cell)}
                    onChange={(e) => onCell(ri, ci, e.target.value)}
                  />
                ) : (
                  <span>{cell}</span>
                )}
                {showSol && solution && <span className="projection-sol-val">{sol}</span>}
              </div>
            );
          }),
        )}
      </div>
    </div>
  );
}

export function ProjectionFillGrids({ views, editable, values, onChange, solutionOverlay }: Props) {
  const keys = (["front", "right", "top"] as const).filter((k) => views[k]?.length);

  function patch(key: "top" | "front" | "right", ri: number, ci: number, v: string) {
    const base = cloneGrid(values[key] ?? views[key]);
    setCell(base, ri, ci, v);
    onChange({ ...values, [key]: base });
  }

  const titles = { front: "Vorderansicht", right: "Rechtsansicht", top: "Aufsicht" };

  return (
    <div className="projection-fill-grids stack">
      {keys.map((k) => (
        <ViewBlock
          key={k}
          title={titles[k]}
          grid={values[k] ?? views[k]}
          editable={editable}
          solution={solutionOverlay?.[k]}
          onCell={(ri, ci, v) => patch(k, ri, ci, v)}
        />
      ))}
    </div>
  );
}
