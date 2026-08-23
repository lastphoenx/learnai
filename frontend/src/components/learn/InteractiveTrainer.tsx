"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  deferLearnQuestion,
  fetchLearnState,
  fetchProfile,
  markFlashcardStatus,
  patchChildLearnGoals,
  submitCardInputAnswer,
  submitLearnAnswer,
  submitPracticeAnswer,
  type GoalsProgressBlock,
  type LearnState,
  type SttProvider,
} from "@/lib/api";
import { CardInputExercise } from "@/components/learn/CardInputExercise";
import { JumpStrip } from "@/components/learn/JumpStrip";
import { QuizWeaknessPanel } from "@/components/QuizWeaknessPanel";
import { PracticeExercise } from "@/components/learn/PracticeExercise";
import { formatQuizOption, quizOptionClassName } from "@/lib/quizOption";
import { QuizExplanation } from "@/components/learn/QuizExplanation";
import {
  cardJumpClassName,
  cardJumpTitle,
  countAnsweredInDeck,
  firstOpenQuizIndex,
  getStoredQuizAnswer,
  hasOtherOpenQuizQuestions,
  isQuizAnswered,
  nextOpenQuizIndex,
  orderCardsWithDeferred,
  quizJumpClassName,
  quizJumpTitle,
  quizQuestionKey,
} from "@/lib/quizNav";

type CardFilter = "due" | "all" | "merk" | "mental" | "input" | "practice";

function cardKind(card: { kind?: string }): string {
  return card.kind || "mental";
}

function GoalsBlock({ title, block }: { title: string; block: GoalsProgressBlock }) {
  if (!block.active_count) return null;
  return (
    <div className="trainer-goals-block">
      <h4 className="trainer-goals-title">{title}</h4>
      {block.headline && <p className="trainer-goals-headline">{block.headline}</p>}
      {block.deadline && (
        <p className="muted trainer-goals-deadline">
          Ziel bis {block.deadline}
          {block.days_left != null && block.days_left >= 0 ? ` (${block.days_left} Tage)` : ""}
          {block.overdue ? " — überfällig" : ""}
        </p>
      )}
      <ul className="trainer-goals-list">
        {block.items.map((item) => (
          <li key={item.key} className={item.met ? "trainer-goal-met" : ""}>
            <div className="trainer-goal-row">
              <span>{item.label}</span>
              <strong>
                {item.done}
                {item.target != null ? ` / ${item.target}` : ""}
                {item.bonus > 0 ? ` (+${item.bonus})` : ""}
              </strong>
            </div>
            {item.target != null && (
              <div className="trainer-progress-bar" aria-hidden="true">
                <div
                  className="trainer-progress-fill"
                  style={{ width: `${Math.min(100, item.percent ?? 0)}%` }}
                />
              </div>
            )}
            {item.message && <p className="muted trainer-goal-msg">{item.message}</p>}
          </li>
        ))}
      </ul>
    </div>
  );
}

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
  const goalsProgress = trainer?.goals_progress;
  const [childGoalQuiz, setChildGoalQuiz] = useState("");
  const [childGoalMerk, setChildGoalMerk] = useState("");
  const [tab, setTab] = useState<Tab>("home");
  const [cardIndex, setCardIndex] = useState(0);
  const [deferredCardKeys, setDeferredCardKeys] = useState<string[]>([]);
  const [flipped, setFlipped] = useState(false);
  const [quizIndex, setQuizIndex] = useState(0);
  const [quizChallenge, setQuizChallenge] = useState(false);
  const [quizWeakOnly, setQuizWeakOnly] = useState(false);
  const [quizDeck, setQuizDeck] = useState<QuizItem[]>([]);
  const [cardFilter, setCardFilter] = useState<CardFilter>("due");
  const [practiceIndex, setPracticeIndex] = useState(0);
  const [cardInputResult, setCardInputResult] = useState<{
    correct: boolean;
    result_correct?: boolean;
    worked_correct?: boolean | null;
    worked_feedback?: string | null;
    explanation?: string | null;
    expected?: string | null;
  } | null>(null);
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
  const [sttProvider, setSttProvider] = useState<SttProvider>("browser");

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
  const dueSessionKeys = useRef<Set<string>>(new Set());
  const dueSessionFilter = useRef(cardFilter);
  if (dueSessionFilter.current !== cardFilter) {
    dueSessionKeys.current = new Set();
    dueSessionFilter.current = cardFilter;
  }
  if (cardFilter === "due") {
    for (const card of cards) {
      if (progress[card.card_key]?.due !== false) {
        dueSessionKeys.current.add(card.card_key);
      }
    }
  }
  const filteredCards = useMemo(() => {
    if (cardFilter === "practice") return [];
    let list = cards;
    if (cardFilter === "due") {
      list = list.filter(
        (card) =>
          progress[card.card_key]?.due !== false || dueSessionKeys.current.has(card.card_key),
      );
    } else if (cardFilter === "merk" || cardFilter === "mental" || cardFilter === "input") {
      list = list.filter((card) => cardKind(card) === cardFilter);
    }
    return list;
  }, [cards, cardFilter, progress]);
  const orderedCards = useMemo(
    () => orderCardsWithDeferred(filteredCards, deferredCardKeys),
    [filteredCards, deferredCardKeys],
  );

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
    const profileId = state.unit.profile_id;
    if (!profileId) return;
    fetchProfile(profileId)
      .then((profile) => setSttProvider((profile.stt_provider as SttProvider) || "browser"))
      .catch(() => setSttProvider("browser"));
  }, [state.unit.profile_id]);

  useEffect(() => {
    setCardIndex(0);
    setFlipped(false);
    setCardInputResult(null);
    setDeferredCardKeys([]);
  }, [cardFilter]);

  useEffect(() => {
    if (orderedCards.length === 0) return;
    if (cardIndex >= orderedCards.length) setCardIndex(orderedCards.length - 1);
  }, [cardIndex, orderedCards.length]);

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
  const currentCard = orderedCards[cardIndex];
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
  const canSkipOrDefer = useMemo(() => {
    if (!currentQuestion || quizChallenge || quizWeakOnly) return false;
    if (isQuizAnswered(learnProgress, currentQuestion)) return false;
    return hasOtherOpenQuizQuestions(activeQuestions, learnProgress, quizIndex);
  }, [currentQuestion, quizChallenge, quizWeakOnly, learnProgress, activeQuestions, quizIndex]);

  const knowledgeSections = useMemo(() => {
    const fromApi = trainer?.knowledge_sections;
    if (fromApi && fromApi.length > 0) return fromApi;
    return knowledgeByDomain.map(([domain, items]) => ({
      domain,
      module_id: items[0]?.module_id || "",
      intro: "",
      items: items.map(({ title, text }) => ({ title, text })),
    }));
  }, [trainer?.knowledge_sections, knowledgeByDomain]);

  const quizTotal = allQuestions.length;
  const quizStarted = quizAnsweredCount > 0;
  const quizComplete = quizTotal > 0 && quizAnsweredCount >= quizTotal;
  const quizWrongCount = Math.max(0, state.summary.quiz_total - state.summary.quiz_correct);

  type HomeStep =
    | "understand"
    | "start_quiz"
    | "continue_quiz"
    | "weaknesses"
    | "cards"
    | "review";

  const homeStep: HomeStep = (() => {
    if (quizTotal === 0) return "understand";
    if (!quizStarted) return "understand";
    if (!quizComplete) return "continue_quiz";
    if (weakQuestions.length > 0) return "weaknesses";
    if (newCards > 0) return "cards";
    return "review";
  })();

  const cardPercent = stats?.card_count
    ? Math.round((100 * stats.known_cards) / stats.card_count)
    : 0;
  const quizPercent =
    state.summary.quiz_total > 0
      ? Math.round((100 * state.summary.quiz_correct) / state.summary.quiz_total)
      : null;

  const goToPractice = useCallback(
    (index: number) => {
      if (index < 0 || index >= practiceExercises.length) return;
      setPracticeIndex(index);
      setPracticeResult(null);
    },
    [practiceExercises.length],
  );

  const goToCard = useCallback(
    (index: number) => {
      if (index < 0 || index >= orderedCards.length) return;
      setCardIndex(index);
      setFlipped(false);
      setCardInputResult(null);
    },
    [orderedCards.length],
  );

  const refreshLearnState = useCallback(async () => {
    if (!goalsProgress?.parent?.active_count && !goalsProgress?.child?.active_count) return;
    try {
      const fresh = await fetchLearnState(unitId);
      onStateChange(fresh);
    } catch {
      /* Ziele optional — kein harter Fehler */
    }
  }, [goalsProgress, onStateChange, unitId]);

  const markCard = useCallback(
    async (status: "known" | "review") => {
      const card = orderedCards[cardIndex];
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
        dueSessionKeys.current.add(card.card_key);
        setFlipped(false);
        if (cardIndex + 1 < orderedCards.length) setCardIndex(cardIndex + 1);
        void refreshLearnState();
      } catch (err) {
        setError(err instanceof Error ? err.message : "Speichern fehlgeschlagen");
      } finally {
        setBusy(false);
      }
    },
    [cardIndex, orderedCards, onStateChange, refreshLearnState, setBusy, setError, state, unitId],
  );

  const deferCurrentCard = useCallback(() => {
    const card = orderedCards[cardIndex];
    if (!card || orderedCards.length < 2) return;
    if (deferredCardKeys.includes(card.card_key)) {
      goToCard((cardIndex + 1) % orderedCards.length);
      return;
    }
    const nextKey = orderedCards[(cardIndex + 1) % orderedCards.length].card_key;
    const keys = [...deferredCardKeys, card.card_key];
    const nextList = orderCardsWithDeferred(filteredCards, keys);
    const nextIndex = Math.max(0, nextList.findIndex((item) => item.card_key === nextKey));
    setDeferredCardKeys(keys);
    setCardIndex(nextIndex);
    setFlipped(false);
    setCardInputResult(null);
  }, [cardIndex, deferredCardKeys, filteredCards, goToCard, orderedCards]);

  useEffect(() => {
    if (tab !== "cards" || busy || !currentCard) return;

    function onKeyDown(event: KeyboardEvent) {
      const target = event.target;
      if (
        target instanceof HTMLInputElement ||
        target instanceof HTMLTextAreaElement ||
        target instanceof HTMLSelectElement
      ) {
        return;
      }

      const isInputCard = currentCard ? cardKind(currentCard) === "input" : false;

      if ((event.key === " " || event.key === "Spacebar") && !isInputCard) {
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
      if (!isInputCard && (event.key === "g" || event.key === "G")) {
        event.preventDefault();
        void markCard("known");
        return;
      }
      if (!isInputCard && (event.key === "n" || event.key === "N")) {
        event.preventDefault();
        void markCard("review");
        return;
      }
      if ((event.key === "s" || event.key === "S") && orderedCards.length > 1) {
        event.preventDefault();
        deferCurrentCard();
      }
    }

    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [tab, busy, cardIndex, currentCard, deferCurrentCard, goToCard, markCard, orderedCards.length]);

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

          <div className="trainer-home-hero">
            <p className="trainer-home-phase">
              {homeStep === "understand" && "Schritt 1 — Verstehen"}
              {homeStep === "continue_quiz" && "Schritt 2 — Check"}
              {homeStep === "weaknesses" && "Vertiefen — Schwächen"}
              {homeStep === "cards" && "Schritt 3 — Üben"}
              {homeStep === "review" && "Check abgeschlossen"}
            </p>
            <p className="trainer-home-hint">
              {homeStep === "understand" &&
                "Lies zuerst die Themen im Wissens-Hub, dann starte den Check."}
              {homeStep === "continue_quiz" &&
                `${quizAnsweredCount} von ${quizTotal} Fragen beantwortet — mache weiter.`}
              {homeStep === "weaknesses" &&
                `${weakQuestions.length} Frage${weakQuestions.length === 1 ? "" : "n"} noch unsicher — gezielt nacharbeiten.`}
              {homeStep === "cards" &&
                `${newCards} Lernkarte${newCards === 1 ? "" : "n"} noch nicht geübt.`}
              {homeStep === "review" &&
                `${state.summary.quiz_correct}/${state.summary.quiz_total} richtig${quizPercent != null ? ` (${quizPercent}%)` : ""}${quizWrongCount > 0 ? ` · ${quizWrongCount} Fehler` : ""}.`}
            </p>
            <div className="learn-actions trainer-home-primary">
              {homeStep === "understand" && (
                <>
                  <button type="button" className="btn-primary" onClick={() => setTab("knowledge")}>
                    Tutorial: Verstehen
                  </button>
                  {quizTotal > 0 && (
                    <button type="button" className="ghost" onClick={() => openQuiz({})}>
                      Check starten
                    </button>
                  )}
                </>
              )}
              {homeStep === "continue_quiz" && (
                <button type="button" className="btn-primary" onClick={() => openQuiz({})}>
                  Check fortsetzen (Frage {quizAnsweredCount + 1})
                </button>
              )}
              {homeStep === "weaknesses" && (
                <button type="button" className="btn-primary" onClick={() => openQuiz({ weakOnly: true })}>
                  Schwächen üben ({weakQuestions.length})
                </button>
              )}
              {homeStep === "cards" && (
                <button
                  type="button"
                  className="btn-primary"
                  onClick={() => {
                    setCardFilter("all");
                    setTab("cards");
                  }}
                >
                  Lernkarten starten
                </button>
              )}
              {homeStep === "review" && (
                <button type="button" className="btn-primary" onClick={() => openQuiz({})}>
                  Ergebnis ansehen
                </button>
              )}
            </div>
          </div>

          {goalsProgress &&
            (goalsProgress.parent.active_count > 0 || goalsProgress.child.active_count > 0) && (
              <div className="trainer-stat-panel trainer-goals-panel">
                <h3 className="trainer-stat-heading">Lernziele</h3>
                <GoalsBlock title="Vorgabe" block={goalsProgress.parent} />
                <GoalsBlock title="Mein Extra-Ziel" block={goalsProgress.child} />
                <details className="trainer-child-goals-form">
                  <summary>Eigenes Ziel setzen</summary>
                  <div className="form-row">
                    <label>
                      Extra Quiz
                      <input
                        type="number"
                        min={1}
                        placeholder="z. B. 5"
                        value={childGoalQuiz}
                        onChange={(e) => setChildGoalQuiz(e.target.value)}
                      />
                    </label>
                    <label>
                      Extra Merk
                      <input
                        type="number"
                        min={1}
                        placeholder="z. B. 3"
                        value={childGoalMerk}
                        onChange={(e) => setChildGoalMerk(e.target.value)}
                      />
                    </label>
                    <button
                      type="button"
                      className="btn-sm"
                      disabled={busy}
                      onClick={async () => {
                        setBusy(true);
                        setError(null);
                        try {
                          const body: { quiz?: number; cards?: { merk?: number } } = {};
                          const q = Number(childGoalQuiz);
                          const m = Number(childGoalMerk);
                          if (Number.isFinite(q) && q > 0) body.quiz = q;
                          if (Number.isFinite(m) && m > 0) body.cards = { merk: m };
                          const res = await patchChildLearnGoals(unitId, body);
                          onStateChange({
                            ...state,
                            trainer: state.trainer
                              ? {
                                  ...state.trainer,
                                  child_goals: res.child_goals,
                                  goals_progress: res.goals_progress,
                                }
                              : state.trainer,
                          });
                          setChildGoalQuiz("");
                          setChildGoalMerk("");
                        } catch (err) {
                          setError(err instanceof Error ? err.message : "Ziel speichern fehlgeschlagen");
                        } finally {
                          setBusy(false);
                        }
                      }}
                    >
                      Speichern
                    </button>
                  </div>
                </details>
              </div>
            )}

          {quizTotal > 0 && (
            <div className="trainer-stat-panel">
              <h3 className="trainer-stat-heading">Check</h3>
              <div className="trainer-stat-grid">
                <div className="trainer-stat">
                  <strong>{quizAnsweredCount}</strong>
                  <span> beantwortet</span>
                </div>
                <div className="trainer-stat">
                  <strong>{state.summary.quiz_correct}</strong>
                  <span> richtig</span>
                </div>
                <div className="trainer-stat">
                  <strong>{quizWrongCount}</strong>
                  <span> falsch</span>
                </div>
                <div className="trainer-stat">
                  <strong>{quizPercent ?? 0}%</strong>
                  <span> Treffer</span>
                </div>
              </div>
              <div className="trainer-progress-wrap">
                <div className="trainer-progress-bar" aria-hidden="true">
                  <div
                    className="trainer-progress-fill"
                    style={{ width: `${quizTotal ? Math.round((100 * quizAnsweredCount) / quizTotal) : 0}%` }}
                  />
                </div>
                <p className="trainer-progress-label muted">
                  {quizComplete
                    ? `Alle ${quizTotal} Fragen beantwortet`
                    : `${quizAnsweredCount}/${quizTotal} Fragen im Check`}
                </p>
              </div>
            </div>
          )}

          <div className="trainer-stat-panel">
            <h3 className="trainer-stat-heading">Lernkarten</h3>
            <div className="trainer-stat-grid">
              <div className="trainer-stat">
                <strong>{stats.merk_cards ?? 0}</strong>
                <span> Merk</span>
              </div>
              <div className="trainer-stat">
                <strong>{stats.mental_cards ?? stats.card_count}</strong>
                <span> Kopf</span>
              </div>
              <div className="trainer-stat">
                <strong>{stats.input_cards ?? 0}</strong>
                <span> Eingabe</span>
              </div>
              <div className="trainer-stat">
                <strong>{stats.known_cards}</strong>
                <span> sicher</span>
              </div>
            </div>
            <div className="trainer-progress-wrap">
              <div className="trainer-progress-bar" aria-hidden="true">
                <div className="trainer-progress-fill" style={{ width: `${cardPercent}%` }} />
              </div>
              <p className="trainer-progress-label muted">
                {stats.known_cards}/{stats.card_count} Karten sicher ({cardPercent}%)
                {newCards > 0 ? ` · ${newCards} noch nicht geübt` : ""}
              </p>
            </div>
          </div>

          {trainer?.content_analysis && (
            <div className="trainer-content-analysis">
              <h3 className="trainer-stat-heading">Inhaltsanalyse</h3>
              <p className="muted">{trainer.content_analysis.overview}</p>
              <div className="trainer-analysis-grid">
                <div>
                  <strong>Check (Rechenarten)</strong>
                  <ul className="trainer-analysis-list">
                    {trainer.content_analysis.quiz.operations.map((op) => (
                      <li key={`quiz-${op.key}`}>
                        {op.label}: {op.count} ({op.percent}%)
                      </li>
                    ))}
                  </ul>
                </div>
                <div>
                  <strong>Lernkarten (Rechenarten)</strong>
                  <ul className="trainer-analysis-list">
                    {trainer.content_analysis.cards.operations.map((op) => (
                      <li key={`card-${op.key}`}>
                        {op.label}: {op.count} ({op.percent}%)
                      </li>
                    ))}
                  </ul>
                </div>
                {trainer.content_analysis.quiz.methods && trainer.content_analysis.quiz.methods.length > 0 && (
                  <div>
                    <strong>Check (Lösungswege)</strong>
                    <ul className="trainer-analysis-list">
                      {trainer.content_analysis.quiz.methods.map((op) => (
                        <li key={`quiz-method-${op.key}`}>
                          {op.label}: {op.count} ({op.percent}%)
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
                {trainer.content_analysis.cards.methods && trainer.content_analysis.cards.methods.length > 0 && (
                  <div>
                    <strong>Lernkarten (Lösungswege)</strong>
                    <ul className="trainer-analysis-list">
                      {trainer.content_analysis.cards.methods.map((op) => (
                        <li key={`card-method-${op.key}`}>
                          {op.label}: {op.count} ({op.percent}%)
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            </div>
          )}

          <details className="trainer-more-actions">
            <summary>Weitere Aktionen</summary>
            <div className="learn-actions">
              <button type="button" className="ghost" onClick={() => setTab("knowledge")}>
                Wissens-Hub
              </button>
              <button type="button" className="ghost" onClick={() => openQuiz({})}>
                {quizComplete ? "Check ansehen" : "Check öffnen"}
              </button>
              <button
                type="button"
                className="ghost"
                onClick={() => {
                  setCardFilter(newCards > 0 ? "all" : dueCards > 0 ? "due" : "all");
                  setTab("cards");
                }}
              >
                Lernkarten
              </button>
              {weakQuestions.length > 0 && homeStep !== "weaknesses" && (
                <button type="button" className="ghost" onClick={() => openQuiz({ weakOnly: true })}>
                  Nur Schwächen ({weakQuestions.length})
                </button>
              )}
              <button type="button" className="ghost" onClick={() => openQuiz({ challenge: true })}>
                Quiz-Challenge
              </button>
              <Link href={`/units/${unitId}`} className="btn ghost">
                Pause
              </Link>
            </div>
          </details>

          {state.quiz_weaknesses && (
            <QuizWeaknessPanel unitId={unitId} data={state.quiz_weaknesses} compact />
          )}
        </>
      )}

      {tab === "knowledge" && (
        <>
          <h2>Wissens-Hub</h2>
          <p className="muted trainer-knowledge-intro">
            Schritt 1 — Verstehen: Regeln, Rechenwege und typische Fehler pro Thema. Danach startest du den Check.
          </p>
          {knowledgeSections.length === 0 ? (
            <p className="muted">Noch kein Kernwissen vorhanden.</p>
          ) : (
            <div className="trainer-knowledge-list">
              {knowledgeSections.map((section) => (
                <details
                  key={section.module_id || section.domain}
                  className="trainer-knowledge-block"
                  open={knowledgeSections.length <= 3}
                >
                  <summary className="trainer-knowledge-summary">
                    <span className="trainer-knowledge-domain">{section.domain}</span>
                    <span className="muted">
                      {section.items.length} Merkpunkt{section.items.length === 1 ? "" : "e"}
                    </span>
                  </summary>
                  {section.intro && <p className="trainer-knowledge-intro-block">{section.intro}</p>}
                  <ol className="trainer-knowledge-points">
                    {section.items.map((item, i) => (
                      <li key={`${section.module_id}-${i}`}>
                        <strong>{item.title}</strong>
                        <p>{item.text}</p>
                      </li>
                    ))}
                  </ol>
                </details>
              ))}
            </div>
          )}
          <div className="learn-actions">
            <button type="button" className="btn-primary" onClick={() => openQuiz({})}>
              {quizStarted ? "Weiter zum Check" : "Check starten"}
            </button>
            <button type="button" className="ghost" onClick={() => setTab("home")}>
              Zurück zum Einstieg
            </button>
          </div>
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
              className={cardFilter === "merk" ? "trainer-tab active" : "trainer-tab"}
              onClick={() => setCardFilter("merk")}
            >
              Merk ({stats.merk_cards ?? 0})
            </button>
            <button
              type="button"
              className={cardFilter === "mental" ? "trainer-tab active" : "trainer-tab"}
              onClick={() => setCardFilter("mental")}
            >
              Kurz ({stats.mental_cards ?? stats.card_count})
            </button>
            <button
              type="button"
              className={cardFilter === "input" ? "trainer-tab active" : "trainer-tab"}
              onClick={() => setCardFilter("input")}
            >
              Eingabe ({stats.input_cards ?? 0})
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
            <div className="trainer-cards">
              <div className="quiz-status-row">
                <div className="trainer-progress-wrap">
                  <div className="trainer-progress-bar" aria-hidden="true">
                    <div
                      className="trainer-progress-fill"
                      style={{
                        width: `${Math.round(
                          (100 * (practiceIndex + 1)) / Math.max(1, practiceExercises.length),
                        )}%`,
                      }}
                    />
                  </div>
                </div>
                <p className="learn-quiz-meta muted">
                  {[
                    `Aufgabe ${practiceIndex + 1} von ${practiceExercises.length}`,
                    currentPractice.domain || null,
                  ]
                    .filter(Boolean)
                    .join(" · ")}
                </p>
              </div>
              <JumpStrip
                count={practiceExercises.length}
                currentIndex={practiceIndex}
                disabled={busy}
                ariaLabel="Übungsaufgaben"
                itemKey={(i) => `${practiceExercises[i].module_id}:${practiceExercises[i].exercise_index}`}
                itemClassName={(i) => `quiz-nav-jump${i === practiceIndex ? " active" : ""}`}
                itemTitle={(i) => `Aufgabe ${i + 1}`}
                onSelect={goToPractice}
              />
              <PracticeExercise
                key={`${currentPractice.module_id}:${currentPractice.exercise_index}`}
                exercise={currentPractice}
                exerciseIndex={practiceIndex}
                total={practiceExercises.length}
                busy={busy}
                hideMeta
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
            </div>
          )}

          {cardFilter === "practice" && !currentPractice && (
            <p className="muted">Keine Übungsaufgaben in dieser Einheit — nach «Mit KI aufbereiten» neu generieren.</p>
          )}

          {cardFilter !== "practice" && currentCard && (
            <div className="trainer-cards">
              <div className="quiz-status-row">
                <div className="trainer-progress-wrap">
                  <div className="trainer-progress-bar" aria-hidden="true">
                    <div
                      className="trainer-progress-fill"
                      style={{
                        width: `${Math.round((100 * (cardIndex + 1)) / Math.max(1, orderedCards.length))}%`,
                      }}
                    />
                  </div>
                </div>
                <p className="learn-quiz-meta muted">
                  {[
                    `${
                      cardKind(currentCard) === "merk"
                        ? "Merkkarte"
                        : cardKind(currentCard) === "input"
                          ? "Eingabe-Karte"
                          : "Kurzfrage"
                    } ${cardIndex + 1} von ${orderedCards.length}`,
                    currentCard.domain || null,
                    progress[currentCard.card_key]?.status === "known"
                      ? cardKind(currentCard) === "input"
                        ? "richtig"
                        : "gewusst"
                      : progress[currentCard.card_key]?.status === "review"
                        ? cardKind(currentCard) === "input"
                          ? "falsch"
                          : "wiederholen"
                        : deferredCardKeys.includes(currentCard.card_key)
                          ? "später"
                          : null,
                  ]
                    .filter(Boolean)
                    .join(" · ")}
                </p>
              </div>
              <JumpStrip
                count={orderedCards.length}
                currentIndex={cardIndex}
                disabled={busy}
                ariaLabel="Lernkarten"
                itemKey={(i) => orderedCards[i].card_key}
                itemClassName={(i) => {
                  const card = orderedCards[i];
                  const jumpKind = cardKind(card) === "input" ? "input" : "merk";
                  return cardJumpClassName(i, cardIndex, {
                    kind: jumpKind,
                    status: progress[card.card_key]?.status,
                    deferred: deferredCardKeys.includes(card.card_key),
                  });
                }}
                itemTitle={(i) => {
                  const card = orderedCards[i];
                  const jumpKind = cardKind(card) === "input" ? "input" : "merk";
                  return cardJumpTitle(i, {
                    kind: jumpKind,
                    status: progress[card.card_key]?.status,
                    deferred: deferredCardKeys.includes(card.card_key),
                  });
                }}
                onSelect={goToCard}
              />

              {cardKind(currentCard) === "input" ? (
                <>
                <CardInputExercise
                  key={currentCard.card_key}
                  question={currentCard.question}
                  expectedMethod={currentCard.expected_method}
                  language={state.unit.language || "de"}
                  sttProvider={sttProvider}
                  profileId={state.unit.profile_id || undefined}
                  busy={busy}
                  result={cardInputResult}
                  onSpeechError={setError}
                  onSubmit={async (answer, workedSolution) => {
                    setBusy(true);
                    setError(null);
                    try {
                      const res = await submitCardInputAnswer(unitId, {
                        module_id: currentCard.module_id,
                        card_index: currentCard.card_index,
                        answer,
                        worked_solution: workedSolution,
                      });
                      onStateChange({
                        ...state,
                        progress: res.progress,
                        summary: res.summary,
                        trainer: state.trainer
                          ? {
                              ...state.trainer,
                              flashcard_progress: res.flashcard_progress || {
                                ...state.trainer.flashcard_progress,
                                [res.card_key]: {
                                  ...(state.trainer.flashcard_progress[res.card_key] || {
                                    status: res.correct ? "known" : "review",
                                    attempts: 1,
                                  }),
                                  status: res.correct ? "known" : "review",
                                  due: !res.correct,
                                },
                              },
                            }
                          : state.trainer,
                      });
                      setCardInputResult({
                        correct: res.correct,
                        result_correct: res.result_correct,
                        worked_correct: res.worked_correct,
                        worked_feedback: res.worked_feedback,
                        explanation: res.explanation,
                        expected: res.expected,
                      });
                    } catch (err) {
                      setError(err instanceof Error ? err.message : "Antwort fehlgeschlagen");
                    } finally {
                      setBusy(false);
                    }
                  }}
                />
                <p className="trainer-shortcuts muted">← → = weiter · S = später</p>
                </>
              ) : (
                <>
                  <button
                    type="button"
                    className={`trainer-flashcard${flipped ? " flipped" : ""}`}
                    onClick={() => setFlipped(!flipped)}
                  >
                    <span className="trainer-flashcard-label">{flipped ? "Antwort" : "Frage"}</span>
                    {flipped ? (
                      <div className="trainer-flashcard-answer">
                        <QuizExplanation text={currentCard.answer} />
                        {currentCard.tip ? <p className="muted">{currentCard.tip}</p> : null}
                      </div>
                    ) : (
                      <p>{currentCard.question}</p>
                    )}
                  </button>
                  <p className="trainer-shortcuts muted">
                    Space = umdrehen · ← → = weiter · G = gewusst · N = nochmal · S = später
                  </p>
                </>
              )}

              <div className="learn-actions">
                {cardKind(currentCard) !== "input" && (
                  <>
                    <button type="button" className="ghost btn-review" disabled={busy} onClick={() => void markCard("review")}>
                      Wiederholen (N)
                    </button>
                    <button type="button" className="btn-primary btn-known" disabled={busy} onClick={() => void markCard("known")}>
                      Gewusst (G)
                    </button>
                  </>
                )}
                {orderedCards.length > 1 && (
                  <button
                    type="button"
                    className="ghost"
                    disabled={busy}
                    title="Karte ans Ende legen, ohne Bewertung"
                    onClick={deferCurrentCard}
                  >
                    Später
                  </button>
                )}
              </div>
            </div>
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
        <div className="trainer-quiz">
          <div className="quiz-status-row">
            <div className="trainer-progress-wrap">
              <div className="trainer-progress-bar" aria-hidden="true">
                <div
                  className="trainer-progress-fill"
                  style={{
                    width: `${Math.round(
                      (100 * (quizIndex + 1)) / Math.max(1, activeQuestions.length),
                    )}%`,
                  }}
                />
              </div>
            </div>
            <p className="learn-quiz-meta muted">
              {[
                `Frage ${quizIndex + 1} von ${activeQuestions.length}`,
                isReviewMode ? "Ansicht" : null,
                currentQuestion.domain || null,
                quizChallenge ? "Challenge" : quizWeakOnly ? "nur Schwächen" : "Check",
              ]
                .filter(Boolean)
                .join(" · ")}
            </p>
          </div>
          <JumpStrip
            count={activeQuestions.length}
            currentIndex={quizIndex}
            disabled={busy}
            ariaLabel="Quiz-Fragen"
            itemKey={(i) => quizQuestionKey(activeQuestions[i])}
            itemClassName={(i) => quizJumpClassName(i, quizIndex, learnProgress, activeQuestions[i])}
            itemTitle={(i) => quizJumpTitle(i, learnProgress, activeQuestions[i])}
            onSelect={goToQuizQuestion}
          />
          <p className="learn-quiz-question">{currentQuestion.q}</p>
          <div className="quiz-options">
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
            <div className="quiz-answer-block">
              {isReviewMode ? (
                <p className="quiz-review-heading muted">Gespeicherte Antwort</p>
              ) : answerResult.correct ? (
                <p className="quiz-verdict ok">Richtig!</p>
              ) : (
                <p className="quiz-verdict bad">Nicht ganz — schau nochmal hin.</p>
              )}
              {answerResult.explanation && <QuizExplanation text={answerResult.explanation} />}
            </div>
          )}
          {!answerResult ? (
            <div className="learn-actions">
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
            </div>
          ) : isReviewMode && nextOpenQuizIndex(activeQuestions, learnProgress, quizIndex) != null ? (
            <div className="learn-actions">
              <button type="button" className="btn-primary" onClick={() => skipToNextOpen()}>
                Nächste offene Frage
              </button>
            </div>
          ) : isReviewMode ? (
            <div className="quiz-finish-actions">
              <button type="button" className="btn-primary" onClick={finishQuiz}>
                Zurück zum Einstieg
              </button>
            </div>
          ) : (
            <div className="learn-actions">
              <button
                type="button"
                className="btn-primary"
                onClick={() => advanceAfterAnswer(state.progress)}
              >
                {nextOpenQuizIndex(activeQuestions, state.progress, quizIndex) != null
                  ? "Nächste Frage"
                  : "Fertig"}
              </button>
            </div>
          )}
        </div>
      )}
    </section>
  );
}
