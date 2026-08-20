"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import {
  markFlashcardStatus,
  submitLearnAnswer,
  type LearnState,
} from "@/lib/api";

type Tab = "home" | "knowledge" | "cards" | "quiz";

type QuizItem = {
  q: string;
  options?: string[];
  answer?: number;
  explanation?: string;
  module_id: string;
  question_index: number;
  domain?: string;
};

type Props = {
  unitId: string;
  state: LearnState;
  busy: boolean;
  setBusy: (v: boolean) => void;
  setError: (msg: string | null) => void;
  onStateChange: (next: LearnState) => void;
};

function shuffle<T>(items: T[]): T[] {
  const copy = [...items];
  for (let i = copy.length - 1; i > 0; i -= 1) {
    const j = Math.floor(Math.random() * (i + 1));
    [copy[i], copy[j]] = [copy[j], copy[i]];
  }
  return copy;
}

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
  const [quizChallenge, setQuizChallenge] = useState(false);
  const [quizDeck, setQuizDeck] = useState<QuizItem[]>([]);
  const [cardFilter, setCardFilter] = useState<"due" | "all">("due");
  const [selected, setSelected] = useState<number | null>(null);
  const [answerResult, setAnswerResult] = useState<{
    correct: boolean;
    correct_index: number;
    explanation?: string;
  } | null>(null);

  const cards = trainer?.cards || [];
  const knowledge = trainer?.knowledge || [];
  const knowledgeByDomain = useMemo(() => {
    const map = new Map<string, typeof knowledge>();
    for (const item of knowledge) {
      const key = item.domain || "Allgemein";
      const list = map.get(key) || [];
      list.push(item);
      map.set(key, list);
    }
    return [...map.entries()];
  }, [knowledge]);
  const progress = trainer?.flashcard_progress || {};
  const filteredCards = useMemo(() => {
    if (cardFilter === "all") return cards;
    return cards.filter((card) => progress[card.card_key]?.due !== false);
  }, [cards, cardFilter, progress]);

  useEffect(() => {
    setCardIndex(0);
    setFlipped(false);
  }, [cardFilter]);

  const allQuestions = useMemo(
    () =>
      (state.modules || []).flatMap((mod) => {
        const quiz = mod.quiz as {
          questions?: { q: string; options?: string[]; answer?: number; explanation?: string }[];
        };
        return (quiz?.questions || []).map((q, i) => ({
          ...q,
          module_id: mod.id,
          question_index: i,
          domain: mod.title,
        }));
      }),
    [state.modules],
  );

  const activeQuestions = quizDeck.length > 0 ? quizDeck : allQuestions;
  const currentCard = filteredCards[cardIndex];
  const currentQuestion = activeQuestions[quizIndex];

  const stats = trainer?.stats;
  const dueCards = stats?.due_cards ?? filteredCards.length;
  const cardPercent = stats?.card_count
    ? Math.round((100 * stats.known_cards) / stats.card_count)
    : 0;
  const quizPercent =
    state.summary.quiz_total > 0
      ? Math.round((100 * state.summary.quiz_correct) / state.summary.quiz_total)
      : null;

  const goToCard = useCallback(
    (index: number) => {
      if (index < 0 || index >= filteredCards.length) return;
      setCardIndex(index);
      setFlipped(false);
    },
    [filteredCards.length],
  );

  const markCard = useCallback(
    async (status: "known" | "review") => {
      const card = filteredCards[cardIndex];
      if (!card) return;
      setBusy(true);
      setError(null);
      try {
        const res = await markFlashcardStatus(unitId, {
          module_id: card.module_id,
          card_index: card.card_index,
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
                  known_cards: Object.values(res.flashcard_progress).filter((p) => p.status === "known")
                    .length,
                  review_cards: Object.values(res.flashcard_progress).filter((p) => p.status === "review")
                    .length,
                  due_cards: state.trainer.cards.filter(
                    (c) => res.flashcard_progress[c.card_key]?.due !== false,
                  ).length,
                },
              }
            : state.trainer,
        });
        setFlipped(false);
        if (cardIndex + 1 < filteredCards.length) setCardIndex(cardIndex + 1);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Speichern fehlgeschlagen");
      } finally {
        setBusy(false);
      }
    },
    [cardIndex, filteredCards, onStateChange, setBusy, setError, state, unitId],
  );

  useEffect(() => {
    if (tab !== "cards" || busy) return;

    function onKeyDown(event: KeyboardEvent) {
      const target = event.target;
      if (
        target instanceof HTMLInputElement ||
        target instanceof HTMLTextAreaElement ||
        target instanceof HTMLSelectElement
      ) {
        return;
      }

      if (event.key === " " || event.key === "Spacebar") {
        event.preventDefault();
        setFlipped((value) => !value);
        return;
      }
      if (event.key === "ArrowLeft") {
        event.preventDefault();
        goToCard(cardIndex - 1);
        return;
      }
      if (event.key === "ArrowRight") {
        event.preventDefault();
        goToCard(cardIndex + 1);
        return;
      }
      if (event.key === "g" || event.key === "G") {
        event.preventDefault();
        void markCard("known");
        return;
      }
      if (event.key === "n" || event.key === "N") {
        event.preventDefault();
        void markCard("review");
      }
    }

    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [tab, busy, cardIndex, goToCard, markCard]);

  function openQuiz(challenge: boolean) {
    setQuizChallenge(challenge);
    setQuizDeck(challenge ? shuffle(allQuestions) : allQuestions);
    setQuizIndex(0);
    setSelected(null);
    setAnswerResult(null);
    setTab("quiz");
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

  if (!trainer || !stats) {
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
            onClick={() => {
              if (key === "quiz") openQuiz(false);
              else setTab(key);
            }}
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
              <strong>{stats.known_cards}</strong>
              <span> sicher</span>
            </div>
            <div className="trainer-stat">
              <strong>{dueCards}</strong>
              <span> fällig</span>
            </div>
            <div className="trainer-stat">
              <strong>{stats.review_cards}</strong>
              <span> wiederholen</span>
            </div>
            <div className="trainer-stat">
              <strong>{stats.card_count}</strong>
              <span> gesamt</span>
            </div>
          </div>
          <div className="trainer-progress-wrap">
            <div className="trainer-progress-bar" aria-hidden="true">
              <div className="trainer-progress-fill" style={{ width: `${cardPercent}%` }} />
            </div>
            <p className="trainer-progress-label muted">
              {stats.known_cards}/{stats.card_count} Karten sicher ({cardPercent}%)
              {dueCards > 0 ? ` · ${dueCards} heute fällig` : ""}
              {quizPercent !== null ? ` · Quiz ${state.summary.quiz_correct}/${state.summary.quiz_total} (${quizPercent}%)` : ""}
            </p>
          </div>
          <div className="learn-actions">
            <button
              type="button"
              className="btn-primary"
              onClick={() => {
                setCardFilter(dueCards > 0 ? "due" : "all");
                setTab("cards");
              }}
            >
              {dueCards > 0 ? "Fällige Karten" : "Lernkarten starten"}
            </button>
            <button type="button" className="ghost" onClick={() => openQuiz(true)}>
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
          <p className="muted trainer-knowledge-intro">
            Kurzüberblick pro Thema — vor den Lernkarten lesen oder zwischendurch nachschlagen.
          </p>
          {knowledgeByDomain.length === 0 ? (
            <p className="muted">Noch kein Kernwissen vorhanden.</p>
          ) : (
            <div className="trainer-knowledge-list">
              {knowledgeByDomain.map(([domain, items]) => (
                <details
                  key={domain}
                  className="trainer-knowledge-block"
                  open={knowledgeByDomain.length <= 3}
                >
                  <summary className="trainer-knowledge-summary">
                    <span className="trainer-knowledge-domain">{domain}</span>
                    <span className="muted">
                      {items.length} Merkpunkt{items.length === 1 ? "" : "e"}
                    </span>
                  </summary>
                  <ul className="trainer-knowledge-points">
                    {items.map((item, i) => (
                      <li key={`${item.module_id}-${i}`}>
                        {item.title && item.title !== domain && <strong>{item.title}</strong>}
                        <p>{item.text}</p>
                      </li>
                    ))}
                  </ul>
                </details>
              ))}
            </div>
          )}
        </>
      )}

      {tab === "cards" && currentCard && (
        <>
          <div className="trainer-card-filter">
            <button
              type="button"
              className={cardFilter === "due" ? "trainer-tab active" : "trainer-tab"}
              onClick={() => setCardFilter("due")}
            >
              Fällig ({dueCards})
            </button>
            <button
              type="button"
              className={cardFilter === "all" ? "trainer-tab active" : "trainer-tab"}
              onClick={() => setCardFilter("all")}
            >
              Alle ({stats.card_count})
            </button>
          </div>
          <p className="learn-quiz-meta muted">
            Karte {cardIndex + 1} von {filteredCards.length}
            {progress[currentCard.card_key]?.status === "known"
              ? " · gewusst"
              : progress[currentCard.card_key]?.status === "review"
                ? " · wiederholen"
                : ""}
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
          <p className="trainer-shortcuts muted">Space = umdrehen · ← → = Karte · G = gewusst · N = nochmal</p>
          <div className="learn-actions">
            <button type="button" className="ghost" disabled={busy || cardIndex === 0} onClick={() => goToCard(cardIndex - 1)}>
              Zurück
            </button>
            <button type="button" className="ghost" disabled={busy} onClick={() => void markCard("review")}>
              Wiederholen (N)
            </button>
            <button type="button" className="btn-primary" disabled={busy} onClick={() => void markCard("known")}>
              Gewusst (G)
            </button>
          </div>
        </>
      )}

      {tab === "cards" && !currentCard && (
        <p className="muted">
          {cardFilter === "due"
            ? "Keine fälligen Karten — alles erledigt für heute."
            : "Keine Lernkarten vorhanden."}
        </p>
      )}

      {tab === "quiz" && currentQuestion && (
        <>
          <p className="learn-quiz-meta muted">
            Frage {quizIndex + 1} von {activeQuestions.length} · {currentQuestion.domain}
            {quizChallenge ? " · Challenge" : ""}
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
                  if (quizIndex + 1 < activeQuestions.length) setQuizIndex(quizIndex + 1);
                }}
              >
                {quizIndex + 1 < activeQuestions.length ? "Nächste Frage" : "Fertig"}
              </button>
            )}
          </div>
        </>
      )}
    </section>
  );
}
