"use client";

import { FormEvent, useState } from "react";

export type PracticeItem = {
  prompt: string;
  hint?: string | null;
  answer_type?: "text" | "number" | string;
};

type Props = {
  exercise: PracticeItem;
  exerciseIndex: number;
  total: number;
  busy: boolean;
  result: { correct: boolean; hint?: string | null; expected?: string | null } | null;
  onSubmit: (answer: string) => void;
  onContinue: () => void;
};

export function PracticeExercise({
  exercise,
  exerciseIndex,
  total,
  busy,
  result,
  onSubmit,
  onContinue,
}: Props) {
  const [value, setValue] = useState("");
  const isNumber = exercise.answer_type === "number";

  function onFormSubmit(e: FormEvent) {
    e.preventDefault();
    if (!value.trim() || result) return;
    onSubmit(value.trim());
  }

  return (
    <div className="practice-exercise stack">
      <p className="learn-quiz-meta muted">
        Übung {exerciseIndex + 1} von {total}
        {isNumber ? " · Zahl eingeben" : " · Antwort eingeben"}
      </p>
      <p className="learn-quiz-question">{exercise.prompt}</p>
      {exercise.hint && !result && <p className="muted practice-hint">Tipp: {exercise.hint}</p>}
      <form onSubmit={onFormSubmit} className="practice-form">
        <input
          type={isNumber ? "text" : "text"}
          inputMode={isNumber ? "decimal" : "text"}
          className="practice-input"
          placeholder={isNumber ? "z.B. 3/4 oder 0.75" : "Deine Antwort"}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          disabled={busy || Boolean(result)}
        />
        {!result ? (
          <button type="submit" className="btn-primary" disabled={busy || !value.trim()}>
            Prüfen
          </button>
        ) : (
          <button type="button" className="btn-primary" onClick={onContinue} disabled={busy}>
            Weiter
          </button>
        )}
      </form>
      {result && (
        <div className={`learn-feedback ${result.correct ? "ok" : "bad"}`}>
          {result.correct ? (
            <strong style={{ color: "var(--accent)" }}>Richtig!</strong>
          ) : (
            <>
              <strong style={{ color: "var(--danger)" }}>Noch nicht — versuch es nochmal oder lies den Tipp.</strong>
              {result.expected && (
                <p className="muted" style={{ margin: "0.35rem 0 0" }}>
                  Lösung: {result.expected}
                </p>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
}
