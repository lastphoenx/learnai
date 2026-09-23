"use client";

import { useMemo, useState } from "react";
import type { TrainerSyntheticViewpointConfig } from "@/lib/api";
import { BuildingIsoPreview } from "@/components/learn/BuildingIsoPreview";
import { ViewpointPlan, viewpointCandidateLabel } from "@/components/learn/ViewpointPlan";

type Props = {
  config: TrainerSyntheticViewpointConfig;
  busy: boolean;
  result: { correct: boolean; expected_label?: string | null } | null;
  onSubmit: (answer: string) => void;
  onContinue: () => void;
};

export function SyntheticViewpointExercise({ config, busy, result, onSubmit, onContinue }: Props) {
  const matrix = useMemo(() => config.height_matrix ?? [[1]], [config.height_matrix]);
  const candidates = config.candidates?.length ? config.candidates : [];
  const [picked, setPicked] = useState<string | null>(null);

  function choose(id: string) {
    if (result || busy) return;
    setPicked(id);
    onSubmit(id);
  }

  return (
    <div className="synthetic-viewpoint stack">
      <p className="muted">
        Das Gebäude ist mit <strong>Vorne / Hinten / Links / Rechts</strong> beschriftet — die Beschriftung dreht mit dem Modell.
        Wähle den Standpunkt, von dem die Aufgabe beschrieben wird.
      </p>
      <ViewpointPlan matrix={matrix} candidates={candidates} selectedId={picked} />
      <BuildingIsoPreview matrix={matrix} showOrientationLabels={true} />
      <div className="viewpoint-choice-list stack" style={{ gap: "0.5rem" }}>
        {candidates.map((c) => (
          <button
            key={c.id}
            type="button"
            className="btn-secondary viewpoint-choice-btn"
            style={{ textAlign: "left", justifyContent: "flex-start" }}
            disabled={busy || Boolean(result)}
            onClick={() => choose(c.id)}
          >
            <span className="viewpoint-choice-id">{c.id}</span>
            <span>{viewpointCandidateLabel(c)}</span>
          </button>
        ))}
      </div>
      {result && (
        <div className={`learn-feedback ${result.correct ? "ok" : "bad"}`}>
          {result.correct ? (
            <strong style={{ color: "var(--accent)" }}>Richtig!</strong>
          ) : (
            <strong style={{ color: "var(--danger)" }}>
              Erwartet: {result.expected_label ?? "—"}
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
