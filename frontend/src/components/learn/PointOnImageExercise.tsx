"use client";

import { useState } from "react";
import { sourceFileUrl, type TrainerPointOnImageConfig } from "@/lib/api";

type Props = {
  unitId: string;
  config: TrainerPointOnImageConfig;
  busy: boolean;
  result: { correct: boolean; expected?: string | null } | null;
  onSubmit: (answer: string) => void;
  onContinue: () => void;
};

export function PointOnImageExercise({ unitId, config, busy, result, onSubmit, onContinue }: Props) {
  const [selected, setSelected] = useState<string | null>(null);
  const bg = config.background;
  const bgUrl = sourceFileUrl(unitId, bg.source_id);
  const bbox = bg.bbox || { x: 0, y: 0, w: 1, h: 1 };
  const w = bbox.w;
  const h = bbox.h;
  const imgWidthPct = 100 / w;
  const imgHeightPct = 100 / h;
  const leftPct = (-bbox.x / w) * 100;
  const topPct = (-bbox.y / h) * 100;

  return (
    <div className="point-on-image-exercise stack">
      {config.reference?.source_id && config.reference.bbox && (
        <div className="point-on-image-reference">
          <p className="muted">Welcher Standort passt zu diesem Foto?</p>
          {/* reference shown via parent prompt context — optional crop omitted for brevity */}
        </div>
      )}
      <div
        className="point-on-image-stage"
        style={{ position: "relative", overflow: "hidden", aspectRatio: `${w} / ${h}` }}
      >
        <img
          src={bgUrl}
          alt="Karte"
          draggable={false}
          style={{
            position: "absolute",
            width: `${imgWidthPct}%`,
            height: `${imgHeightPct}%`,
            left: `${leftPct}%`,
            top: `${topPct}%`,
            maxWidth: "none",
          }}
        />
        {config.candidates.map((c) => {
          const left = `${c.x * 100}%`;
          const top = `${c.y * 100}%`;
          const isSel = selected === c.id;
          return (
            <button
              key={c.id}
              type="button"
              className={`point-on-image-hotspot${isSel ? " selected" : ""}${
                result?.correct && isSel ? " ok" : ""
              }${result && !result.correct && isSel ? " bad" : ""}`}
              style={{ left, top }}
              disabled={busy || Boolean(result)}
              aria-label={`Standort ${c.id}`}
              onClick={() => {
                setSelected(c.id);
                onSubmit(c.id);
              }}
            >
              {c.id}
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
                  Richtige Antwort: Standort {result.expected}
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
