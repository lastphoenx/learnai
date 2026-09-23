"use client";

import { useMemo } from "react";
import type { TrainerGridFillConfig } from "@/lib/api";
import { BuildingIsoPreview } from "@/components/learn/BuildingIsoPreview";
import { GridFillWorkshopExercise } from "@/components/learn/gridFill/GridFillWorkshopExercise";
import {
  GridFillPlanEditor,
  useGridFillPlanState,
} from "@/components/learn/gridFill/GridFillPlanEditor";
import { normalizeGridSizeHint } from "@/lib/spatialGridSize";

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

function isGridFillWorkshopV2(config: TrainerGridFillConfig): boolean {
  return (
    config.presentation === "workshop_v2"
    && config.validation === "derived_projection"
    && Boolean(config.reference_height_matrix?.length)
  );
}

export function GridFillExercise(props: Props) {
  if (isGridFillWorkshopV2(props.config)) {
    return <GridFillWorkshopExercise {...props} />;
  }
  return <GridFillClassicExercise {...props} />;
}

function GridFillClassicExercise({ config, busy, result, onSubmit, onContinue }: Props) {
  const { rows: configRows, cols: configCols, cell_type } = config;
  const gridSizeHint = normalizeGridSizeHint(config.grid_size_hint);
  const isNumber = cell_type === "number";
  const { size, setSize, grid, setGrid } = useGridFillPlanState(config);
  const rows = gridSizeHint === "derive" ? size.rows : configRows;
  const cols = gridSizeHint === "derive" ? size.cols : configCols;

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
      <GridFillPlanEditor
        config={config}
        busy={busy}
        locked={Boolean(result)}
        grid={grid}
        setGrid={setGrid}
        size={size}
        setSize={setSize}
        slotMap={slotMap}
      />
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
