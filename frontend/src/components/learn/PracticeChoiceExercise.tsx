"use client";

import { useState } from "react";
import { formatQuizOption, quizOptionClassName } from "@/lib/quizOption";

type Props = {
  prompt: string;
  hint?: string | null;
  options: string[];
  busy: boolean;
  result: {
    correct: boolean;
    expected?: string | null;
    correct_index?: number | null;
  } | null;
  onSubmit: (optionIndex: number) => void;
  onContinue: () => void;
};

export function PracticeChoiceExercise({
  prompt,
  hint,
  options,
  busy,
  result,
  onSubmit,
  onContinue,
}: Props) {
  const [selected, setSelected] = useState<number | null>(null);
  const answerResult =
    result && selected !== null
      ? {
          correct: result.correct,
          correct_index: result.correct_index ?? -1,
          attempts: 1,
        }
      : null;

  function pick(index: number) {
    if (result || busy) return;
    setSelected(index);
    onSubmit(index);
  }

  return (
    <div className="practice-choice stack">
      <div className="quiz-options" role="listbox" aria-label="Antworten">
        {options.map((option, index) => (
          <button
            key={`${index}-${option}`}
            type="button"
            role="option"
            className={quizOptionClassName(index, selected, answerResult)}
            disabled={busy || Boolean(result)}
            onClick={() => pick(index)}
          >
            {formatQuizOption(option, index)}
          </button>
        ))}
      </div>
      {result && (
        <div className={`learn-feedback ${result.correct ? "ok" : "bad"}`}>
          {result.correct ? (
            <strong style={{ color: "var(--accent)" }}>Richtig!</strong>
          ) : (
            <>
              <strong style={{ color: "var(--danger)" }}>Noch nicht — lies den Merksatz im Wissens-Hub.</strong>
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
