"use client";

import { useEffect, useMemo, useState } from "react";
import type { TrainerNetBuildConfig } from "@/lib/api";

type Props = {
  config: TrainerNetBuildConfig;
  busy: boolean;
  result: { correct: boolean } | null;
  onSubmit: (answerJson: string) => void;
  onContinue: () => void;
};

function cellsToSet(cells: [number, number][] | undefined): Set<string> {
  const s = new Set<string>();
  for (const pair of cells || []) {
    if (pair.length === 2) s.add(`${pair[0]},${pair[1]}`);
  }
  return s;
}

export function NetBuildExercise({ config, busy, result, onSubmit, onContinue }: Props) {
  const { rows, cols, mode = "build", given_cells } = config;
  const validateMode = mode === "validate" && Boolean(given_cells?.length);
  const locked = useMemo(() => cellsToSet(given_cells), [given_cells]);

  const [selected, setSelected] = useState<Set<string>>(() => (validateMode ? locked : new Set()));

  useEffect(() => {
    if (validateMode) setSelected(locked);
  }, [validateMode, locked]);

  const selectedList = useMemo(() => {
    const out: [number, number][] = [];
    for (const key of selected) {
      const [c, r] = key.split(",").map((n) => parseInt(n, 10));
      if (!Number.isNaN(c) && !Number.isNaN(r)) out.push([c, r]);
    }
    out.sort((a, b) => a[0] - b[0] || a[1] - b[1]);
    return out;
  }, [selected]);

  function toggle(ri: number, ci: number) {
    if (result || validateMode) return;
    const key = `${ci},${ri}`;
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else if (next.size < 6) next.add(key);
      return next;
    });
  }

  return (
    <div className="net-build-exercise stack">
      <p className="muted">
        {validateMode
          ? "Das vorgegebene Netz ist markiert. Entscheide: lässt es sich zu einem Würfel falten?"
          : "Tippe genau 6 zusammenhängende Felder für ein Würfelnetz an."}
      </p>
      <div className="grid-fill-table" style={{ gridTemplateColumns: `repeat(${cols}, minmax(2.5rem, 1fr))` }}>
        {Array.from({ length: rows }, (_, ri) =>
          Array.from({ length: cols }, (_, ci) => {
            const key = `${ci},${ri}`;
            const on = selected.has(key);
            return (
              <button
                key={key}
                type="button"
                className={`grid-fill-cell net-build-cell${on ? " selected" : ""}${validateMode && on ? " net-build-given" : ""}`}
                disabled={busy || Boolean(result) || validateMode}
                onClick={() => toggle(ri, ci)}
                aria-pressed={on}
              />
            );
          }),
        )}
      </div>
      {!validateMode && <p className="muted">{selected.size}/6 Felder</p>}
      {!result ? (
        validateMode ? (
          <div className="btnrow" style={{ display: "flex", gap: "0.75rem", flexWrap: "wrap" }}>
            <button type="button" className="btn-primary" disabled={busy} onClick={() => onSubmit(JSON.stringify(true))}>
              Ja — gültiges Würfelnetz
            </button>
            <button type="button" className="btn-secondary" disabled={busy} onClick={() => onSubmit(JSON.stringify(false))}>
              Nein — ungültig
            </button>
          </div>
        ) : (
          <button
            type="button"
            className="btn-primary"
            disabled={busy || selected.size !== 6}
            onClick={() => onSubmit(JSON.stringify(selectedList))}
          >
            Prüfen
          </button>
        )
      ) : (
        <div className={`learn-feedback ${result.correct ? "ok" : "bad"}`}>
          {result.correct ? (
            <strong style={{ color: "var(--accent)" }}>{validateMode ? "Richtig!" : "Gültiges Würfelnetz!"}</strong>
          ) : (
            <strong style={{ color: "var(--danger)" }}>
              {validateMode ? "Noch nicht — lies die Aufgabe nochmal." : "Noch nicht — prüfe Zusammenhang und Form."}
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
