"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import {
  markFlashcardStatus,
  submitLearnAnswer,
  type LearnState,
} from "@/lib/api";

type Tab = "home" | "knowledge" | "cards" | "quiz";

type Props = {
  unitId: string;
  state: LearnState;
  busy: boolean;
  setBusy: (v: boolean) => void;
  setError: (msg: string | null) => void;
  onStateChange: (next: LearnState) => void;
};

export function InteractiveTrainer({
  unitId,
  state,
  busy,
  setBusy,
  setError,
  onStateChange,
}: Props) {
  const trainer = state.trainer;
  const [tab, setTab] = useState<Tab>("home");
  const [cardIndex, setCardIndex] = useState(0);
  const [flipped, setFlipped] = useState(false);
  const [quizIndex, setQuizIndex] = useState(0);
  const [selected, setSelected] = useState<number | null>(null);
  const [answerResult, setAnswerResult] = useState<{
    correct: boolean;
    correct_index: number;
    explanation?: string;
  } | null>(null);

  const cards = trainer?.cards || [];
  const knowledge = trainer?.knowledge || [];
  const allQuestions = useMemo(
    () =>
      (state.modules || []).flatMap((mod) => {
        const quiz = mod.quiz as { questions?: { q: string; options?: string[]; answer?: number; explanation?: string }[] };
        return (quiz?.questions || []).map((q, i) => ({
          ...q,
          module_id: mod.id,
          question_index: i,
          domain: mod.title,
        }));
      }),
    [state.modules],
  );

  const currentCard = cards[cardIndex];
  const currentQuestion = allQuestions[quizIndex];
  const progress = trainer?.flashcard_progress || {};

  async function markCard(status: "known" | "review") {
    if (!currentCard) return;
    setBusy(true);
    setError(null);
    try {
      const res = await markFlashcardStatus(unitId, {
        module_id: currentCard.module_id,
        card_index: currentCard.card_index,
        status,
      });
      onStateChange({
        ...state,
        trainer: state.trainer
          ? {
              ...state.trainer,
              flashcard_progress: res.flashcard_progress,
              stats: {
                ...state.trainer.stats,
                known_cards: Object.values(res.flashcard_progress).filter((p) => p.status === "known").length,
                review_cards: Object.values(res.flashcard_progress).filter((p) => p.status === "review").length,
              },
            }
          : state.trainer,
      });
      setFlipped(false);
      if (cardIndex + 1 < cards.length) setCardIndex(cardIndex + 1);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Speichern fehlgeschlagen");
    } finally {
      setBusy(false);
    }
  }

  async function submitQuiz() {
    if (!currentQuestion || selected === null) return;
    setBusy(true);
    setError(null);
    try {
      const res = await submitLearnAnswer(unitId, {
        module_id: currentQuestion.module_id,
        question_index: currentQuestion.question_index,
        selected,
      });
      setAnswerResult({
        correct: res.correct,
        correct_index: res.correct_index,
        explanation: res.explanation,
      });
      onStateChange({
        ...state,
        progress: res.progress,
        summary: res.summary,
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Antwort fehlgeschlagen");
    } finally {
      setBusy(false);
    }
  }

  if (!trainer) {
    return <p className="muted">Trainer-Daten fehlen — bitte Seite neu laden.</p>;
  }

  return (
    <section className="card learn-phase-card stack interactive-trainer">
      <div className="trainer-tabs">
        {(
          [
            ["home", "Start"],
            ["knowledge", "Wissen"],
            ["cards", "Lernkarten"],
            ["quiz", "Quiz"],
          ] as const
        ).map(([key, label]) => (
          <button
            key={key}
            type="button"
            className={tab === key ? "trainer-tab active" : "trainer-tab"}
            onClick={() => setTab(key)}
          >
            {label}
          </button>
        ))}
      </div>

      {tab === "home" && (
        <>
          <h2>{state.unit.title}</h2>
          <p className="muted">Interaktiver Lerntrainer</p>
          <div className="trainer-stat-grid">
            <div className="trainer-stat">
              <strong>{trainer.stats.card_count}</strong>
              <span>Lernkarten</span>
            </div>
            <div className="trainer-stat">
              <strong>{trainer.stats.question_count}</strong>
              <span>Quizfragen</span>
            </div>
            <div className="trainer-stat">
              <strong>{trainer.stats.known_cards}</strong>
              <span>Gewusst</span>
            </div>
          </div>
          <div className="learn-actions">
            <button type="button" className="btn-primary" onClick={() => setTab("cards")}>
              Lernkarten starten
            </button>
            <button type="button" className="ghost" onClick={() => setTab("quiz")}>
              Quiz-Challenge
            </button>
            <Link href={`/units/${unitId}`} className="btn ghost">
              Pause
            </Link>
          </div>
        </>
      )}

      {tab === "knowledge" && (
        <>
          <h2>Wissens-Hub</h2>
          <ul className="trainer-knowledge-list">
            {knowledge.map((item, i) => (
              <li key={i} className="trainer-knowledge-item">
                <span className="badge badge-mode">{item.domain}</span>
                <strong>{item.title}</strong>
                <p>{item.text}</p>
              </li>
            ))}
          </ul>
        </>
      )}

      {tab === "cards" && currentCard && (
        <>
          <p className="learn-quiz-meta muted">
            Karte {cardIndex + 1} von {cards.length}
            {progress[currentCard.card_key]?.status === "known" ? " · gewusst" : ""}
          </p>
          <button
            type="button"
            className={`trainer-flashcard${flipped ? " flipped" : ""}`}
            onClick={() => setFlipped(!flipped)}
          >
            <span className="trainer-flashcard-label">{flipped ? "Antwort" : "Frage"}</span>
            <p>{flipped ? currentCard.answer : currentCard.question}</p>
            {flipped && currentCard.tip && <p className="muted">{currentCard.tip}</p>}
          </button>
          <div className="learn-actions">
            <button type="button" className="ghost" disabled={busy} onClick={() => markCard("review")}>
              Wiederholen
            </button>
            <button type="button" className="btn-primary" disabled={busy} onClick={() => markCard("known")}>
              Gewusst
            </button>
          </div>
        </>
      )}

      {tab === "quiz" && currentQuestion && (
        <>
          <p className="learn-quiz-meta muted">
            Frage {quizIndex + 1} von {allQuestions.length} · {currentQuestion.domain}
          </p>
          <p className="learn-quiz-question">{currentQuestion.q}</p>
          <div>
            {(currentQuestion.options || []).map((opt, i) => (
              <button
                key={i}
                type="button"
                className={`learn-quiz-option${selected === i ? " selected" : ""}${
                  answerResult
                    ? i === answerResult.correct_index
                      ? " correct"
                      : i === selected
                        ? " wrong"
                        : ""
                    : ""
                }`}
                disabled={busy || Boolean(answerResult)}
                onClick={() => setSelected(i)}
              >
                {opt}
              </button>
            ))}
          </div>
          {answerResult && answerResult.explanation && (
            <p className="muted">{answerResult.explanation}</p>
          )}
          <div className="learn-actions">
            {!answerResult ? (
              <button type="button" className="btn-primary" disabled={busy || selected === null} onClick={submitQuiz}>
                Antwort prüfen
              </button>
            ) : (
              <button
                type="button"
                className="btn-primary"
                onClick={() => {
                  setAnswerResult(null);
                  setSelected(null);
                  if (quizIndex + 1 < allQuestions.length) setQuizIndex(quizIndex + 1);
                }}
              >
                {quizIndex + 1 < allQuestions.length ? "Nächste Frage" : "Fertig"}
              </button>
            )}
          </div>
        </>
      )}
    </section>
  );
}
