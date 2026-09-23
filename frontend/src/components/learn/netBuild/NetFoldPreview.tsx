"use client";

import { cubeNetFoldLabels } from "@/lib/cubeNetFold";

type Props = {
  rows: number;
  cols: number;
  selected: Set<string>;
};

export function NetFoldPreview({ rows, cols, selected }: Props) {
  const cells: [number, number][] = [];
  for (const key of selected) {
    const [c, r] = key.split(",").map((n) => parseInt(n, 10));
    if (!Number.isNaN(c) && !Number.isNaN(r)) cells.push([c, r]);
  }
  cells.sort((a, b) => a[0] - b[0] || a[1] - b[1]);

  const labels = cells.length === 6 ? cubeNetFoldLabels(cells) : null;
  const valid = labels !== null;

  return (
    <div className="net-fold-preview stack">
      <p className="muted" style={{ margin: 0 }}>
        <strong>Faltvorschau</strong> — gleiche Farbe = gleiche Würfelfläche nach dem Falten.
      </p>
      {cells.length < 6 ? (
        <p className="muted">Wähle 6 Felder, um die Zuordnung zu sehen.</p>
      ) : !valid ? (
        <p className="muted" style={{ color: "var(--danger)" }}>
          Diese 6 Felder ergeben kein gültiges Würfelnetz (Überlappung oder falsche Form).
        </p>
      ) : (
        <>
          <div
            className="grid-fill-table net-fold-preview-grid"
            style={{ gridTemplateColumns: `repeat(${cols}, minmax(1.5rem, 1fr))` }}
          >
            {Array.from({ length: rows }, (_, ri) =>
              Array.from({ length: cols }, (_, ci) => {
                const key = `${ci},${ri}`;
                const meta = labels?.[key];
                return (
                  <div
                    key={key}
                    className={`grid-fill-cell net-build-cell${meta ? " selected" : ""}`}
                    style={meta ? { background: meta.color, borderColor: meta.color } : undefined}
                    aria-hidden={!meta}
                  >
                    {meta ? <span className="net-fold-label">{meta.label}</span> : null}
                  </div>
                );
              }),
            )}
          </div>
          <ul className="net-fold-legend muted" style={{ fontSize: "0.85rem", paddingLeft: "1.1rem" }}>
            {Object.values(labels!).reduce(
              (acc, v) => (acc.some((x) => x.label === v.label) ? acc : [...acc, v]),
              [] as { label: string; color: string }[],
            ).map((v) => (
              <li key={v.label}>
                <span style={{ display: "inline-block", width: 12, height: 12, background: v.color, marginRight: 6 }} />
                {v.label} = eine Würfelfläche
              </li>
            ))}
          </ul>
        </>
      )}
    </div>
  );
}
