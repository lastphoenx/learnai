"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { SpeechInputButton } from "@/components/SpeechInputButton";
import { QuizExplanation } from "@/components/learn/QuizExplanation";
import type { SttProvider } from "@/lib/api";

const BLANK = "___";

type Props = {
  question: string;
  language?: string;
  sttProvider?: SttProvider;
  profileId?: string;
  busy: boolean;
  result: {
    correct: boolean;
    explanation?: string | null;
    expected?: string | null;
  } | null;
  onSubmit: (answer: string) => void;
  onSpeechError?: (message: string) => void;
};

function splitCloze(question: string): string[] {
  const src = question || "";
  if (!src.includes(BLANK)) return [src];
  return src.split(BLANK);
}

export function ClozeExercise({
  question,
  language = "de",
  sttProvider = "browser",
  profileId,
  busy,
  result,
  onSubmit,
  onSpeechError,
}: Props) {
  const parts = useMemo(() => splitCloze(question), [question]);
  const blankCount = Math.max(0, parts.length - 1);
  const [values, setValues] = useState<string[]>(() => Array(blankCount).fill(""));

  useEffect(() => {
    setValues(Array(blankCount).fill(""));
  }, [question, blankCount]);

  function updateBlank(index: number, value: string) {
    setValues((prev) => {
      const next = [...prev];
      next[index] = value;
      return next;
    });
  }

  function onFormSubmit(e: FormEvent) {
    e.preventDefault();
    if (result || blankCount < 1) return;
    const joined = values.map((v) => v.trim()).join("|");
    if (!joined.replace(/\|/g, "").trim()) return;
    onSubmit(joined);
  }

  return (
    <div className="cloze-exercise stack">
      <form onSubmit={onFormSubmit} className="cloze-form">
        <p className="learn-quiz-question cloze-question-line">
          {parts.map((part, index) => (
            <span key={`${index}-${part.slice(0, 12)}`}>
              {part}
              {index < blankCount ? (
                <input
                  type="text"
                  className="cloze-inline-input"
                  value={values[index] ?? ""}
                  disabled={busy || Boolean(result)}
                  aria-label={`Lücke ${index + 1}`}
                  onChange={(e) => updateBlank(index, e.target.value)}
                />
              ) : null}
            </span>
          ))}
        </p>
        {!result && (
          <div className="learn-actions">
            <button type="submit" className="btn-primary" disabled={busy}>
              Antwort prüfen
            </button>
            {blankCount === 1 && (
              <SpeechInputButton
                language={language}
                sttProvider={sttProvider}
                profileId={profileId}
                disabled={busy}
                title="Antwort diktieren"
                onTranscript={(text, finalChunk) => {
                  if (!finalChunk) return;
                  updateBlank(0, text.trim());
                }}
                onError={onSpeechError}
              />
            )}
          </div>
        )}
      </form>
      {result && (
        <div className="quiz-answer-block">
          <p className={result.correct ? "quiz-verdict ok" : "quiz-verdict bad"}>
            {result.correct ? "Richtig!" : "Noch nicht ganz — lies die Erklärung."}
          </p>
          {result.explanation && <QuizExplanation text={result.explanation} />}
          {!result.correct && result.expected && (
            <p className="muted">Erwartet: {result.expected.replace(/\|/g, ", ")}</p>
          )}
        </div>
      )}
    </div>
  );
}
