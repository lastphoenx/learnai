"use client";

import { useMemo, useState } from "react";
import type { TrainerNetBuildConfig } from "@/lib/api";

type Props = {
  config: TrainerNetBuildConfig;
  busy: boolean;
  result: { correct: boolean } | null;
  onSubmit: (answerJson: string) => void;
  onContinue: () => void;
};

export function NetBuildExercise({ config, busy, result, onSubmit, onContinue }: Props) {
  const { rows, cols } = config;
  const [selected, setSelected] = useState<Set<string>>(new Set());

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
    if (result) return;
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
      <p className="muted">Tippe genau 6 zusammenhängende Felder für ein Würfelnetz an.</p>
      <div className="grid-fill-table" style={{ gridTemplateColumns: `repeat(${cols}, minmax(2.5rem, 1fr))` }}>
        {Array.from({ length: rows }, (_, ri) =>
          Array.from({ length: cols }, (_, ci) => {
            const key = `${ci},${ri}`;
            const on = selected.has(key);
            return (
              <button
                key={key}
                type="button"
                className={`grid-fill-cell net-build-cell${on ? " selected" : ""}`}
                disabled={busy || Boolean(result)}
                onClick={() => toggle(ri, ci)}
                aria-pressed={on}
              />
            );
          }),
        )}
      </div>
      <p className="muted">{selected.size}/6 Felder</p>
      {!result ? (
        <button type="button" className="btn-primary" disabled={busy || selected.size !== 6} onClick={() => onSubmit(JSON.stringify(selectedList))}>
          Prüfen
        </button>
      ) : (
        <div className={`learn-feedback ${result.correct ? "ok" : "bad"}`}>
          {result.correct ? <strong style={{ color: "var(--accent)" }}>Gültiges Würfelnetz!</strong> : <strong style={{ color: "var(--danger)" }}>Noch nicht — prüfe Zusammenhang und Form.</strong>}
          <button type="button" className="btn-primary" onClick={onContinue} disabled={busy} style={{ marginTop: "0.75rem" }}>
            Weiter
          </button>
        </div>
      )}
    </div>
  );
}
