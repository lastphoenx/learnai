"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import {
  deferLearnQuestion,
  markFlashcardStatus,
  submitLearnAnswer,
  submitPracticeAnswer,
  type LearnState,
} from "@/lib/api";
import { QuizWeaknessPanel } from "@/components/QuizWeaknessPanel";
import { PracticeExercise } from "@/components/learn/PracticeExercise";
import { formatQuizOption, formatQuizExplanation, quizOptionClassName } from "@/lib/quizOption";
import {
  countAnsweredInDeck,
  firstOpenQuizIndex,
  getStoredQuizAnswer,
  hasOtherOpenQuizQuestions,
  isQuizAnswered,
  isQuizDeferred,
  nextOpenQuizIndex,
  quizQuestionKey,
} from "@/lib/quizNav";

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
  const [quizWeakOnly, setQuizWeakOnly] = useState(false);
  const [quizDeck, setQuizDeck] = useState<QuizItem[]>([]);
  const [cardFilter, setCardFilter] = useState<"due" | "all" | "practice">("due");
  const [practiceIndex, setPracticeIndex] = useState(0);
  const [practiceResult, setPracticeResult] = useState<{
    correct: boolean;
    hint?: string | null;
    expected?: string | null;
  } | null>(null);
  const [autoTrainerId, setAutoTrainerId] = useState<string | null>(null);
  const [selected, setSelected] = useState<number | null>(null);
  const [answerResult, setAnswerResult] = useState<{
    correct: boolean;
    correct_index: number;
    explanation?: string;
  } | null>(null);
  const [lastSubmittedKey, setLastSubmittedKey] = useState<string | null>(null);

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
    if (cardFilter === "practice") return [];
    return cards.filter((card) => progress[card.card_key]?.due !== false);
  }, [cards, cardFilter, progress]);

  const practiceExercises = useMemo(
    () =>
      (state.modules || []).flatMap((mod) => {
        const items = (mod.content as { practice?: { prompt: string; hint?: string; answer_type?: string }[] })
          ?.practice;
        return (items || []).map((exercise, exerciseIndex) => ({
          ...exercise,
          module_id: mod.id,
          exercise_index: exerciseIndex,
          domain: mod.title,
        }));
      }),
    [state.modules],
  );
  const currentPractice = practiceExercises[practiceIndex];

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

  const weakKeys = useMemo(() => {
    const keys = new Set<string>();
    for (const w of state.quiz_weaknesses?.weaknesses || []) {
      keys.add(`${w.module_id}:${w.question_index}`);
    }
    return keys;
  }, [state.quiz_weaknesses]);

  const weakQuestions = useMemo(
    () => allQuestions.filter((q) => weakKeys.has(`${q.module_id}:${q.question_index}`)),
    [allQuestions, weakKeys],
  );

  const activeQuestions = quizDeck.length > 0 ? quizDeck : allQuestions;
  const currentCard = filteredCards[cardIndex];
  const currentQuestion = activeQuestions[quizIndex];
  const learnProgress = state.progress;
  const currentStoredAnswer = currentQuestion
    ? getStoredQuizAnswer(learnProgress, currentQuestion)
    : null;
  const isReviewMode = Boolean(
    currentStoredAnswer &&
      answerResult &&
      currentQuestion &&
      quizQuestionKey(currentQuestion) !== lastSubmittedKey,
  );

  const stats = trainer?.stats;
  const newCards = stats?.new_cards ?? Math.max(0, (stats?.card_count ?? 0) - (stats?.known_cards ?? 0) - (stats?.review_cards ?? 0));
  const reviewDueCards = Math.max(0, (stats?.due_cards ?? 0) - newCards);
  const dueCards = stats?.due_cards ?? filteredCards.length;
  const quizAnsweredCount = useMemo(
    () => countAnsweredInDeck(allQuestions, learnProgress),
    [allQuestions, learnProgress],
  );
  const checkQuizAnsweredCount = useMemo(
    () => countAnsweredInDeck(activeQuestions, learnProgress),
    [activeQuestions, learnProgress],
  );
  const canSkipOrDefer = useMemo(() => {
    if (!currentQuestion || quizChallenge || quizWeakOnly) return false;
    if (isQuizAnswered(learnProgress, currentQuestion)) return false;
    return hasOtherOpenQuizQuestions(activeQuestions, learnProgress, quizIndex);
  }, [currentQuestion, quizChallenge, quizWeakOnly, learnProgress, activeQuestions, quizIndex]);

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

  const goToQuizQuestion = useCallback(
    (index: number) => {
      if (index < 0 || index >= activeQuestions.length) return;
      setQuizIndex(index);
      const q = activeQuestions[index];
      const stored = getStoredQuizAnswer(learnProgress, q);
      if (stored) {
        setSelected(stored.selected);
        setAnswerResult(stored);
      } else {
        setSelected(null);
        setAnswerResult(null);
      }
    },
    [activeQuestions, learnProgress],
  );

  function openQuiz(options: { challenge?: boolean; weakOnly?: boolean } = {}) {
    const challenge = Boolean(options.challenge);
    const weakOnly = Boolean(options.weakOnly);
    setQuizChallenge(challenge);
    setQuizWeakOnly(weakOnly);
    let deck = weakOnly ? weakQuestions : allQuestions;
    if (challenge) deck = shuffle(deck);
    setQuizDeck(deck);
    const startIndex = challenge || weakOnly ? 0 : firstOpenQuizIndex(deck, learnProgress);
    setTab("quiz");
    setQuizIndex(startIndex);
    const q = deck[startIndex];
    const stored = q ? getStoredQuizAnswer(learnProgress, q) : null;
    if (stored) {
      setSelected(stored.selected);
      setAnswerResult(stored);
    } else {
      setSelected(null);
      setAnswerResult(null);
    }
  }

  async function deferCurrentQuestion() {
    if (!currentQuestion || isQuizAnswered(learnProgress, currentQuestion)) return;
    setBusy(true);
    setError(null);
    try {
      const res = await deferLearnQuestion(unitId, {
        module_id: currentQuestion.module_id,
        question_index: currentQuestion.question_index,
      });
      const nextProgress = res.progress;
      onStateChange({ ...state, progress: nextProgress, summary: res.summary });
      const next = nextOpenQuizIndex(activeQuestions, nextProgress, quizIndex);
      if (next != null) {
        const q = activeQuestions[next];
        const stored = q ? getStoredQuizAnswer(nextProgress, q) : null;
        setQuizIndex(next);
        setSelected(stored?.selected ?? null);
        setAnswerResult(stored);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Später speichern fehlgeschlagen");
    } finally {
      setBusy(false);
    }
  }

  function finishQuiz() {
    setTab("home");
    setQuizDeck([]);
    setAnswerResult(null);
    setSelected(null);
    setLastSubmittedKey(null);
  }

  function skipToNextOpen() {
    const next = nextOpenQuizIndex(activeQuestions, learnProgress, quizIndex);
    if (next != null) goToQuizQuestion(next);
  }

  function advanceAfterAnswer(progress = learnProgress) {
    const next = nextOpenQuizIndex(activeQuestions, progress, quizIndex);
    if (next == null) {
      finishQuiz();
      return;
    }
    const q = activeQuestions[next];
    const stored = q ? getStoredQuizAnswer(progress, q) : null;
    setQuizIndex(next);
    setSelected(stored?.selected ?? null);
    setAnswerResult(stored);
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
      onStateChange({
        ...state,
        progress: res.progress,
        summary: res.summary,
        quiz_weaknesses: res.quiz_weaknesses ?? state.quiz_weaknesses,
      });
      if (res.auto_trainer_unit_id) {
        setAutoTrainerId(res.auto_trainer_unit_id);
      }
      setAnswerResult({
        correct: res.correct,
        correct_index: res.correct_index,
        explanation: res.explanation,
      });
      if (currentQuestion) {
        setLastSubmittedKey(quizQuestionKey(currentQuestion));
      }
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
      {autoTrainerId && (
        <p className="auto-trainer-notice">
          Schwächen erkannt — KI-Trainer wird erstellt.{" "}
          <Link href={`/units/${autoTrainerId}/learn`}>Zum Trainer</Link>
        </p>
      )}
      <div className="trainer-tabs">
        {(
          [
            ["home", "Einstieg"],
            ["knowledge", "Verstehen"],
            ["cards", "Üben"],
            ["quiz", "Check"],
          ] as const
        ).map(([key, label]) => (
          <button
            key={key}
            type="button"
            className={tab === key ? "trainer-tab active" : "trainer-tab"}
            onClick={() => {
              if (key === "quiz") openQuiz({});
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
          <p className="muted">Lernpfad: Verstehen → Check → Üben → Vertiefen bei Schwächen</p>
          <ol className="trainer-didactic-path muted">
            <li>
              <strong>Verstehen</strong> — Wissens-Hub als Tutorial-Einstieg
            </li>
            <li>
              <strong>Check</strong> — erste Lernkontrolle im Quiz
            </li>
            <li>
              <strong>Üben</strong> — Lernkarten mit Wiederholung
            </li>
            <li>
              <strong>Vertiefen</strong> — bei Fehlern Nacharbeit oder Schwächen-Trainer
            </li>
          </ol>
          <div className="trainer-stat-grid">
            <div className="trainer-stat">
              <strong>{stats.known_cards}</strong>
              <span> sicher</span>
            </div>
            <div className="trainer-stat">
              <strong>{newCards > 0 ? newCards : reviewDueCards}</strong>
              <span>{newCards > 0 ? " offen" : " fällig"}</span>
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
              {newCards > 0
                ? ` · ${newCards} Karten noch nicht geübt`
                : reviewDueCards > 0
                  ? ` · ${reviewDueCards} heute fällig`
                  : ""}
              {quizPercent !== null ? ` · Quiz ${state.summary.quiz_correct}/${state.summary.quiz_total} (${quizPercent}%)` : ""}
            </p>
          </div>
          <div className="learn-actions">
            <button
              type="button"
              className="btn-primary"
              onClick={() => setTab("knowledge")}
            >
              Tutorial: Verstehen
            </button>
            <button type="button" className="ghost" onClick={() => openQuiz({})}>
              {quizAnsweredCount >= allQuestions.length && allQuestions.length > 0
                ? "Check: abgeschlossen — ansehen"
                : quizAnsweredCount > 0 && quizAnsweredCount < allQuestions.length
                  ? `Check: weiter bei Frage ${quizAnsweredCount + 1}`
                  : "Check: Quiz starten"}
            </button>
            <button
              type="button"
              className="btn-primary"
              onClick={() => {
                setCardFilter(newCards > 0 ? "all" : dueCards > 0 ? "due" : "all");
                setTab("cards");
              }}
            >
              {newCards > 0 ? "Üben: Lernkarten starten" : dueCards > 0 ? "Üben: fällige Karten" : "Üben: Lernkarten"}
            </button>
            {weakQuestions.length > 0 && (
              <button type="button" className="ghost" onClick={() => openQuiz({ weakOnly: true })}>
                Check: nur Schwächen ({weakQuestions.length})
              </button>
            )}
            <button type="button" className="ghost" onClick={() => openQuiz({ challenge: true })}>
              Quiz-Challenge
            </button>
            <Link href={`/units/${unitId}`} className="btn ghost">
              Pause
            </Link>
          </div>
          {state.quiz_weaknesses && (
            <QuizWeaknessPanel unitId={unitId} data={state.quiz_weaknesses} compact />
          )}
        </>
      )}

      {tab === "knowledge" && (
        <>
          <h2>Wissens-Hub</h2>
          <p className="muted trainer-knowledge-intro">
            Schritt 1 — Heranführung: Kurzüberblick pro Thema, tutorial-artig vor Check und Üben.
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

      {tab === "cards" && (
        <>
          <div className="trainer-card-filter">
            <button
              type="button"
              className={cardFilter === "due" ? "trainer-tab active" : "trainer-tab"}
              onClick={() => setCardFilter("due")}
            >
              Fällig ({reviewDueCards > 0 ? reviewDueCards : newCards})
            </button>
            <button
              type="button"
              className={cardFilter === "all" ? "trainer-tab active" : "trainer-tab"}
              onClick={() => setCardFilter("all")}
            >
              Alle ({stats.card_count})
            </button>
            {practiceExercises.length > 0 && (
              <button
                type="button"
                className={cardFilter === "practice" ? "trainer-tab active" : "trainer-tab"}
                onClick={() => {
                  setCardFilter("practice");
                  setPracticeIndex(0);
                  setPracticeResult(null);
                }}
              >
                Aufgaben ({practiceExercises.length})
              </button>
            )}
          </div>

          {cardFilter === "practice" && currentPractice && (
            <>
              <p className="muted">{currentPractice.domain}</p>
              <PracticeExercise
                exercise={currentPractice}
                exerciseIndex={practiceIndex}
                total={practiceExercises.length}
                busy={busy}
                result={practiceResult}
                onSubmit={async (answer) => {
                  setBusy(true);
                  setError(null);
                  try {
                    const res = await submitPracticeAnswer(unitId, {
                      module_id: currentPractice.module_id,
                      exercise_index: currentPractice.exercise_index,
                      answer,
                    });
                    onStateChange({ ...state, progress: res.progress, summary: res.summary });
                    setPracticeResult({
                      correct: res.correct,
                      hint: res.hint,
                      expected: res.expected,
                    });
                  } catch (err) {
                    setError(err instanceof Error ? err.message : "Antwort fehlgeschlagen");
                  } finally {
                    setBusy(false);
                  }
                }}
                onContinue={() => {
                  setPracticeResult(null);
                  if (practiceIndex + 1 < practiceExercises.length) {
                    setPracticeIndex(practiceIndex + 1);
                  }
                }}
              />
            </>
          )}

          {cardFilter === "practice" && !currentPractice && (
            <p className="muted">Keine Übungsaufgaben in dieser Einheit — nach «Mit KI aufbereiten» neu generieren.</p>
          )}

          {cardFilter !== "practice" && currentCard && (
            <>
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

          {cardFilter !== "practice" && !currentCard && (
            <p className="muted">
              {cardFilter === "due"
                ? "Keine fälligen Karten — alles erledigt für heute."
                : "Keine Lernkarten vorhanden."}
            </p>
          )}
        </>
      )}

      {tab === "quiz" && currentQuestion && (
        <>
          <div className="quiz-nav-row">
            <button
              type="button"
              className="ghost"
              disabled={busy || quizIndex <= 0}
              onClick={() => goToQuizQuestion(quizIndex - 1)}
            >
              ← Zurück
            </button>
            <span className="learn-quiz-meta muted">
              Frage {quizIndex + 1} von {activeQuestions.length}
              {isReviewMode ? " · Ansicht (beantwortet)" : ""}
            </span>
            <button
              type="button"
              className="ghost"
              disabled={busy || quizIndex + 1 >= activeQuestions.length}
              onClick={() => goToQuizQuestion(quizIndex + 1)}
            >
              Weiter →
            </button>
          </div>
          <div className="quiz-nav-strip" role="tablist" aria-label="Quiz-Fragen">
            {activeQuestions.map((q, i) => {
              let dotClass = "quiz-nav-dot";
              if (i === quizIndex) dotClass += " active";
              if (isQuizAnswered(learnProgress, q)) dotClass += " done";
              else if (isQuizDeferred(learnProgress, q)) dotClass += " deferred";
              return (
                <button
                  key={quizQuestionKey(q)}
                  type="button"
                  className={dotClass}
                  disabled={busy}
                  title={`Frage ${i + 1}${isQuizAnswered(learnProgress, q) ? " (beantwortet)" : ""}`}
                  onClick={() => goToQuizQuestion(i)}
                />
              );
            })}
          </div>
          <p className="learn-quiz-meta muted">
            {currentQuestion.domain}
            {quizChallenge ? " · Challenge" : quizWeakOnly ? " · nur Schwächen" : " · Check"}
            {!quizChallenge && !quizWeakOnly && checkQuizAnsweredCount > 0
              ? ` · ${checkQuizAnsweredCount}/${activeQuestions.length} beantwortet`
              : ""}
          </p>
          <p className="learn-quiz-question">{currentQuestion.q}</p>
          <div>
            {(currentQuestion.options || []).map((opt, i) => (
              <button
                key={i}
                type="button"
                className={`${quizOptionClassName(i, selected, answerResult)}${isReviewMode ? " readonly" : ""}`}
                disabled={busy || Boolean(answerResult)}
                onClick={() => !answerResult && setSelected(i)}
              >
                {formatQuizOption(opt, i)}
              </button>
            ))}
          </div>
          {answerResult && (
            <div className={`learn-feedback ${answerResult.correct ? "ok" : "bad"}`}>
              {isReviewMode ? (
                <strong className="muted">Gespeicherte Antwort</strong>
              ) : answerResult.correct ? (
                <strong style={{ color: "var(--accent)" }}>Richtig!</strong>
              ) : (
                <strong style={{ color: "var(--danger)" }}>Nicht ganz — schau nochmal hin.</strong>
              )}
              {answerResult.explanation && (
                <p className="muted quiz-explanation-text">{formatQuizExplanation(answerResult.explanation)}</p>
              )}
            </div>
          )}
          <div className="learn-actions">
            {!answerResult ? (
              <>
                <button type="button" className="btn-primary" disabled={busy || selected === null} onClick={submitQuiz}>
                  Antwort prüfen
                </button>
                {canSkipOrDefer && (
                  <>
                    <button
                      type="button"
                      className="ghost"
                      disabled={busy}
                      title="Zur nächsten offenen Frage — diese bleibt offen"
                      onClick={skipToNextOpen}
                    >
                      Überspringen
                    </button>
                    <button
                      type="button"
                      className="ghost"
                      disabled={busy}
                      title="Diese Frage ans Ende der offenen Liste legen"
                      onClick={() => void deferCurrentQuestion()}
                    >
                      Später lösen
                    </button>
                  </>
                )}
              </>
            ) : isReviewMode ? (
              nextOpenQuizIndex(activeQuestions, learnProgress, quizIndex) != null ? (
                <button type="button" className="btn-primary" onClick={() => skipToNextOpen()}>
                  Nächste offene Frage
                </button>
              ) : (
                <button type="button" className="btn-primary" onClick={finishQuiz}>
                  Zurück zum Einstieg
                </button>
              )
            ) : (
              <button
                type="button"
                className="btn-primary"
                onClick={() => advanceAfterAnswer(state.progress)}
              >
                {nextOpenQuizIndex(activeQuestions, state.progress, quizIndex) != null
                  ? "Nächste Frage"
                  : "Fertig"}
              </button>
            )}
          </div>
        </>
      )}
    </section>
  );
}
