"use client";

import { FormEvent, useState } from "react";
import { formatQuizExplanation } from "@/lib/quizOption";
import { useSpeechInput } from "@/lib/useSpeechInput";

type Props = {
  question: string;
  cardIndex: number;
  total: number;
  domain?: string;
  busy: boolean;
  result: {
    correct: boolean;
    result_correct?: boolean;
    worked_correct?: boolean | null;
    worked_feedback?: string | null;
    explanation?: string | null;
    expected?: string | null;
  } | null;
  onSubmit: (answer: string, workedSolution?: string) => void;
  onContinue: () => void;
};

export function CardInputExercise({
  question,
  cardIndex,
  total,
  domain,
  busy,
  result,
  onSubmit,
  onContinue,
}: Props) {
  const [answer, setAnswer] = useState("");
  const [worked, setWorked] = useState("");

  const answerSpeech = useSpeechInput((text) => {
    setAnswer((prev) => (prev ? `${prev} ${text}` : text));
  });
  const workedSpeech = useSpeechInput((text) => {
    setWorked((prev) => (prev ? `${prev} ${text}` : text));
  });

  function onFormSubmit(e: FormEvent) {
    e.preventDefault();
    if (!answer.trim() || result) return;
    onSubmit(answer.trim(), worked.trim() || undefined);
  }

  return (
    <div className="card-input-exercise stack">
      <p className="learn-quiz-meta muted">
        Eingabe-Karte {cardIndex + 1} von {total}
        {domain ? ` · ${domain}` : ""}
      </p>
      <p className="learn-quiz-question">{question}</p>
      <form onSubmit={onFormSubmit} className="practice-form stack">
        <label className="card-input-label">
          Ergebnis
          <div className="card-input-row">
            <input
              type="text"
              inputMode="decimal"
              className="practice-input"
              placeholder="z.B. 3,08"
              value={answer}
              onChange={(e) => setAnswer(e.target.value)}
              disabled={busy || Boolean(result)}
            />
            {answerSpeech.supported && (
              <button
                type="button"
                className={`ghost card-mic-btn${answerSpeech.listening ? " active" : ""}`}
                disabled={busy || Boolean(result)}
                title="Ergebnis diktieren"
                onClick={() => (answerSpeech.listening ? answerSpeech.stop() : answerSpeech.start())}
              >
                {answerSpeech.listening ? "⏹" : "🎤"}
              </button>
            )}
          </div>
        </label>
        <label className="card-input-label">
          Lösungsweg (optional)
          <div className="card-input-row">
            <textarea
              className="practice-input card-worked-input"
              placeholder="Beschreibe deinen Rechenweg …"
              rows={3}
              value={worked}
              onChange={(e) => setWorked(e.target.value)}
              disabled={busy || Boolean(result)}
            />
            {workedSpeech.supported && (
              <button
                type="button"
                className={`ghost card-mic-btn${workedSpeech.listening ? " active" : ""}`}
                disabled={busy || Boolean(result)}
                title="Lösungsweg diktieren"
                onClick={() => (workedSpeech.listening ? workedSpeech.stop() : workedSpeech.start())}
              >
                {workedSpeech.listening ? "⏹" : "🎤"}
              </button>
            )}
          </div>
        </label>
        {!result ? (
          <button type="submit" className="btn-primary" disabled={busy || !answer.trim()}>
            Antwort prüfen
          </button>
        ) : (
          <button type="button" className="btn-primary" onClick={onContinue} disabled={busy}>
            Nächste Karte
          </button>
        )}
      </form>
      {result && (
        <div className={`learn-feedback ${result.correct ? "ok" : "bad"}`}>
          {result.correct ? (
            <strong style={{ color: "var(--accent)" }}>Richtig!</strong>
          ) : (
            <strong style={{ color: "var(--danger)" }}>
              {result.result_correct ? "Ergebnis passt — Lösungsweg noch ergänzen." : "Noch nicht ganz."}
            </strong>
          )}
          {result.worked_feedback && (
            <p className="muted" style={{ margin: "0.35rem 0 0" }}>
              {result.worked_feedback}
            </p>
          )}
          {result.explanation && (
            <p className="muted quiz-explanation-text" style={{ margin: "0.35rem 0 0" }}>
              {formatQuizExplanation(result.explanation)}
            </p>
          )}
          {result.expected && (
            <p className="muted" style={{ margin: "0.35rem 0 0" }}>
              Lösung: {result.expected}
            </p>
          )}
        </div>
      )}
    </div>
  );
}
