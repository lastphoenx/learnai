"use client";

import { useMemo } from "react";
import type { TrainerSyntheticViewpointConfig } from "@/lib/api";
import { BuildingIsoPreview } from "@/components/learn/BuildingIsoPreview";

type Props = {
  config: TrainerSyntheticViewpointConfig;
  busy: boolean;
  result: { correct: boolean; expected_label?: string | null } | null;
  onSubmit: (answer: string) => void;
  onContinue: () => void;
};

export function SyntheticViewpointExercise({ config, busy, result, onSubmit, onContinue }: Props) {
  const matrix = useMemo(() => config.height_matrix ?? [[1]], [config.height_matrix]);
  const candidates = config.candidates?.length ? config.candidates : [{ id: "A" }, { id: "B" }, { id: "C" }];

  return (
    <div className="synthetic-viewpoint stack">
      <p className="muted">Wo steht der Betrachter? (synthetische Szene)</p>
      <BuildingIsoPreview matrix={matrix} showInspector={false} showCameraToggle={true} />
      <div className="image-choice-options">
        {candidates.map((c) => (
          <button
            key={c.id}
            type="button"
            className="btn-secondary"
            disabled={busy || Boolean(result)}
            onClick={() => onSubmit(c.id)}
          >
            {c.id}
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
