"use client";

import { useState } from "react";
import { SourceImageCrop } from "@/components/learn/SourceImageCrop";
import { sourceFileUrl, type TrainerImageChoiceConfig } from "@/lib/api";

type Props = {
  unitId: string;
  config: TrainerImageChoiceConfig;
  busy: boolean;
  result: { correct: boolean; expected?: string | null } | null;
  onSubmit: (optionId: string) => void;
  onContinue: () => void;
};

export function ImageChoiceExercise({ unitId, config, busy, result, onSubmit, onContinue }: Props) {
  const [selected, setSelected] = useState<string | null>(null);
  const reference = config.reference;

  return (
    <div className="image-choice-exercise stack">
      {reference?.source_id && reference.bbox && (
        <div className="image-choice-reference">
          <SourceImageCrop
            url={sourceFileUrl(unitId, reference.source_id)}
            bbox={reference.bbox}
            alt="Aufgabenbild"
          />
        </div>
      )}
      <div className="image-choice-options" role="listbox" aria-label="Bildoptionen">
        {config.options.map((opt) => {
          const isSelected = selected === opt.id;
          const showOk = result?.correct && isSelected;
          const showBad = result && !result.correct && isSelected;
          return (
            <button
              key={opt.id}
              type="button"
              role="option"
              className={`image-choice-option${isSelected ? " selected" : ""}${showOk ? " ok" : ""}${showBad ? " bad" : ""}`}
              disabled={busy || Boolean(result)}
              onClick={() => {
                setSelected(opt.id);
                onSubmit(opt.id);
              }}
            >
              <span className="image-choice-option-label">{opt.id}</span>
              <SourceImageCrop
                url={sourceFileUrl(unitId, opt.source_id)}
                bbox={opt.bbox}
                alt={`Option ${opt.id}`}
              />
            </button>
          );
        })}
      </div>
      {result && (
        <div className={`learn-feedback ${result.correct ? "ok" : "bad"}`}>
          {result.correct ? (
            <strong style={{ color: "var(--accent)" }}>Richtig!</strong>
          ) : (
            <>
              <strong style={{ color: "var(--danger)" }}>Noch nicht.</strong>
              {result.expected && (
                <p className="muted" style={{ margin: "0.35rem 0 0" }}>
                  Richtige Antwort: {result.expected}
                </p>
              )}
            </>
          )}
          <button type="button" className="btn-primary" onClick={onContinue} disabled={busy} style={{ marginTop: "0.75rem" }}>
            Weiter
          </button>
        </div>
      )}
    </div>
  );
}
