"use client";

import { FormEvent, useState } from "react";
import { SpeechInputButton } from "@/components/SpeechInputButton";
import { formatQuizExplanation } from "@/lib/quizOption";
import type { SttProvider } from "@/lib/api";
import { METHOD_LABELS } from "@/lib/api";

type Props = {
  question: string;
  cardIndex: number;
  total: number;
  domain?: string;
  expectedMethod?: string;
  language?: string;
  sttProvider?: SttProvider;
  profileId?: string;
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
  onSpeechError?: (message: string) => void;
};

export function CardInputExercise({
  question,
  cardIndex,
  total,
  domain,
  expectedMethod,
  language = "de",
  sttProvider = "browser",
  profileId,
  busy,
  result,
  onSubmit,
  onContinue,
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
      <p className="learn-quiz-meta muted">
        Eingabe-Karte {cardIndex + 1} von {total}
        {domain ? ` · ${domain}` : ""}
      </p>
      <p className="learn-quiz-question">{question}</p>
      {expectedMethod && (
        <p className="muted card-method-hint">
          Erwarteter Lösungsweg: {METHOD_LABELS[expectedMethod] || expectedMethod}
        </p>
      )}
      <form onSubmit={onFormSubmit} className="practice-form stack">
        <label className="card-input-label">
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
            rows={3}
            value={worked}
            onChange={(e) => setWorked(e.target.value)}
            disabled={busy || Boolean(result)}
          />
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
