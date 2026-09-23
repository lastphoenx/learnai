"use client";

import { useEffect, useMemo, useState } from "react";
import type { TrainerNetBuildConfig } from "@/lib/api";
import { BuildingNetWorkshopShell } from "@/components/learn/buildingWorkshop/BuildingNetWorkshopShell";
import { NetFoldPreview } from "@/components/learn/netBuild/NetFoldPreview";
import {
  netFoldHintAllowed,
  type NetValidatePhase,
} from "@/lib/workshop/netBuildWorkshopGating";

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

const FOLD_PREVIEW_LOCKED_COPY = (
  <p className="muted net-fold-preview-locked">
    <strong>Faltvorschau</strong> ist ausgeblendet. Nutze «Hilfe: Faltvorschau», wenn du die Zuordnung der Würfelflächen
    prüfen willst — nicht vorher, sonst verrät sie die Lösung.
  </p>
);

export function NetBuildWorkshopExercise({ config, busy, result, onSubmit, onContinue }: Props) {
  const { rows, cols, mode = "build", given_cells } = config;
  const validateMode = mode === "validate" && Boolean(given_cells?.length);
  const locked = useMemo(() => cellsToSet(given_cells), [given_cells]);
  const [selected, setSelected] = useState<Set<string>>(() => (validateMode ? locked : new Set()));
  const [validatePhase, setValidatePhase] = useState<NetValidatePhase>("inspect");
  const [foldPreviewUnlocked, setFoldPreviewUnlocked] = useState(false);

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

  const hintAllowed = netFoldHintAllowed({
    validateMode,
    validatePhase,
    selectedCount: selected.size,
  });

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

  const showFoldPreview = foldPreviewUnlocked && hintAllowed;

  return (
    <BuildingNetWorkshopShell
      taskTitle="Würfelnetz"
      taskPrompt={
        validateMode
          ? "Erst das Netz betrachten, dann optional Hilfe, dann entscheiden."
          : "Markiere 6 Felder — die Faltvorschau nur über Hilfe, nicht während du tippst."
      }
      instruction={
        validateMode && validatePhase === "inspect"
          ? "Schritt 1: Sieh dir das vorgegebene Netz an (ohne Falt-Farben)."
          : "Gleiche Farbe in der Faltvorschau = dieselbe Würfelseite. Prüfen kannst du auch ohne Hilfe."
      }
      gridPanel={
        <div className="stack">
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
        </div>
      }
      previewAside={
        showFoldPreview
          ? <NetFoldPreview rows={rows} cols={cols} selected={selected} />
          : FOLD_PREVIEW_LOCKED_COPY
      }
      actions={
        !result
          ? (
              <div className="btnrow" style={{ display: "flex", gap: "0.75rem", flexWrap: "wrap" }}>
                {validateMode && validatePhase === "inspect" && (
                  <button type="button" className="btn btn-secondary" onClick={() => setValidatePhase("decide")}>
                    Weiter zur Entscheidung
                  </button>
                )}
                {!foldPreviewUnlocked && hintAllowed && (
                  <button
                    type="button"
                    className="btn btn-sm btn-secondary"
                    disabled={busy}
                    onClick={() => setFoldPreviewUnlocked(true)}
                  >
                    Hilfe: Faltvorschau anzeigen
                  </button>
                )}
                {validateMode && validatePhase === "decide" && (
                  <>
                    <button type="button" className="btn-primary" disabled={busy} onClick={() => onSubmit(JSON.stringify(true))}>
                      Ja — gültiges Würfelnetz
                    </button>
                    <button type="button" className="btn-secondary" disabled={busy} onClick={() => onSubmit(JSON.stringify(false))}>
                      Nein — ungültig
                    </button>
                  </>
                )}
                {!validateMode && (
                  <button
                    type="button"
                    className="btn-primary"
                    disabled={busy || selected.size !== 6}
                    onClick={() => onSubmit(JSON.stringify(selectedList))}
                  >
                    Prüfen
                  </button>
                )}
              </div>
            )
          : null
      }
      footer={
        result
          ? (
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
            )
          : null
      }
    />
  );
}
