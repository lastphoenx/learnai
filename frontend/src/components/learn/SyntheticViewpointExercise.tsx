"use client";

import { useMemo, useState } from "react";
import type { TrainerSyntheticViewpointConfig } from "@/lib/api";
import { BuildingThreeCanvas } from "@/components/learn/BuildingThreeCanvas";
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
        <strong>Vorne / Hinten / Links / Rechts</strong> am Gebäude; 👁-Marker zeigen mögliche Standpunkte in der 3D-Szene
        (mit dem Gebäude mitverankert). Drehe die Ansicht — Marker und Beschriftung bleiben am Bauwerk.
      </p>
      <ViewpointPlan matrix={matrix} candidates={candidates} selectedId={picked} />
      <p className="muted building-iso-hint">Drehen: ziehen · Zoomen: zwei Finger oder Mausrad · Standpunkt: 👁 antippen</p>
      <BuildingThreeCanvas
        matrix={matrix}
        showOrientationLabels={true}
        heightPx={340}
        viewpointCandidates={candidates}
        selectedViewpointId={picked}
        onViewpointPick={choose}
        viewpointPickDisabled={busy || Boolean(result)}
      />
      <p className="muted">Oder wähle dieselbe Position als Liste:</p>
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
