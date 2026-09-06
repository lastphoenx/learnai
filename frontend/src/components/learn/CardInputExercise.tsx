"use client";

import { FormEvent, useState } from "react";
import { SpeechInputButton } from "@/components/SpeechInputButton";
import { QuizExplanation } from "@/components/learn/QuizExplanation";
import { answerWithVisibleResult } from "@/lib/cardResult";
import type { SttProvider } from "@/lib/api";
import { METHOD_LABELS } from "@/lib/api";

type Props = {
  question: string;
  expectedMethod?: string;
  language?: string;
  sttProvider?: SttProvider;
  profileId?: string;
  busy: boolean;
  result: {
    correct: boolean;
    result_correct?: boolean;
    partial_correct?: boolean;
    partial_reason?: string | null;
    worked_correct?: boolean | null;
    worked_feedback?: string | null;
    explanation?: string | null;
    expected?: string | null;
  } | null;
  onSubmit: (answer: string, workedSolution?: string) => void;
  onSpeechError?: (message: string) => void;
};

export function CardInputExercise({
  question,
  expectedMethod,
  language = "de",
  sttProvider = "browser",
  profileId,
  busy,
  result,
  onSubmit,
  onSpeechError,
}: Props) {
  const [answer, setAnswer] = useState("");
  const [worked, setWorked] = useState("");

  function onFormSubmit(e: FormEvent) {
    e.preventDefault();
    if (!answer.trim() || result) return;
    onSubmit(answer.trim(), worked.trim() || undefined);
  }

  return (
    <div className="card-input-exercise stack">
      <p className="learn-quiz-question">{question}</p>
      {expectedMethod && (
        <p className="muted card-method-hint">
          Erwarteter Lösungsweg: {METHOD_LABELS[expectedMethod] || expectedMethod}
        </p>
      )}
      <form onSubmit={onFormSubmit} className="card-input-form">
        <label className="card-input-label card-input-answer">
          <span className="card-input-label-row">
            Ergebnis
            <SpeechInputButton
              language={language}
              sttProvider={sttProvider}
              profileId={profileId}
              disabled={busy || Boolean(result)}
              title="Ergebnis diktieren"
              onTranscript={(text, finalChunk) => {
                if (!finalChunk) return;
                const chunk = text.trim();
                if (!chunk) return;
                setAnswer((prev) => (prev ? `${prev} ${chunk}` : chunk));
              }}
              onError={onSpeechError}
            />
          </span>
          <input
            type="text"
            inputMode="decimal"
            className="practice-input"
            placeholder="z.B. 3,08"
            value={answer}
            onChange={(e) => setAnswer(e.target.value)}
            disabled={busy || Boolean(result)}
          />
        </label>
        <label className="card-input-label">
          <span className="card-input-label-row">
            Lösungsweg (optional)
            <SpeechInputButton
              language={language}
              sttProvider={sttProvider}
              profileId={profileId}
              continuous
              disabled={busy || Boolean(result)}
              title="Lösungsweg diktieren"
              onTranscript={(text, finalChunk) => {
                if (!finalChunk) return;
                const chunk = text.trim();
                if (!chunk) return;
                setWorked((prev) => (prev ? `${prev} ${chunk}` : chunk));
              }}
              onError={onSpeechError}
            />
          </span>
          <textarea
            className="practice-input card-worked-input"
            placeholder="Beschreibe deinen Rechenweg …"
            rows={5}
            value={worked}
            onChange={(e) => setWorked(e.target.value)}
            disabled={busy || Boolean(result)}
          />
        </label>
        {!result && (
          <div className="card-input-actions">
            <button type="submit" className="btn-primary" disabled={busy || !answer.trim()}>
              Antwort prüfen
            </button>
          </div>
        )}
      </form>
      {result && (
        <div className="quiz-answer-block">
          {result.correct ? (
            <p className="quiz-verdict ok">Richtig!</p>
          ) : result.partial_correct ? (
            <p className="quiz-verdict partial">Fast richtig gedacht!</p>
          ) : (
            <p className="quiz-verdict bad">
              {result.result_correct ? "Ergebnis passt — Lösungsweg noch ergänzen." : "Noch nicht ganz."}
            </p>
          )}
          {result.worked_feedback && <p className="muted">{result.worked_feedback}</p>}
          {result.explanation && (
            <QuizExplanation text={answerWithVisibleResult(question, result.explanation)} />
          )}
          {result.expected && <p className="muted">Lösung: {result.expected}</p>}
        </div>
      )}
    </div>
  );
}
