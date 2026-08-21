import type { LearnProgress } from "@/lib/api";

export type QuizQuestionRef = {
  module_id: string;
  question_index: number;
};

export type StoredQuizAnswer = {
  selected: number;
  correct: boolean;
  correct_index: number;
  explanation?: string;
};

export function quizQuestionKey(q: QuizQuestionRef): string {
  return `${q.module_id}:${q.question_index}`;
}

export function isQuizAnswered(progress: LearnProgress, q: QuizQuestionRef): boolean {
  const answers = progress.modules?.[q.module_id]?.answers ?? [];
  return answers[q.question_index] != null;
}

export function isQuizDeferred(progress: LearnProgress, q: QuizQuestionRef): boolean {
  const deferred = progress.modules?.[q.module_id]?.deferred ?? [];
  return deferred.includes(q.question_index);
}

export function getStoredQuizAnswer(
  progress: LearnProgress,
  q: QuizQuestionRef,
): StoredQuizAnswer | null {
  const mod = progress.modules?.[q.module_id];
  if (!mod) return null;
  const selected = mod.answers?.[q.question_index];
  if (selected == null) return null;
  const details = mod.answer_details?.[String(q.question_index)];
  if (details) return details;
  return { selected, correct: false, correct_index: selected, explanation: undefined };
}

/** Offene Fragen zuerst, auf «Später» verschobene am Ende. */
export function buildOpenQuizIndices<T extends QuizQuestionRef>(
  deck: T[],
  progress: LearnProgress,
): number[] {
  const open: number[] = [];
  const deferred: number[] = [];
  deck.forEach((q, index) => {
    if (isQuizAnswered(progress, q)) return;
    if (isQuizDeferred(progress, q)) deferred.push(index);
    else open.push(index);
  });
  return [...open, ...deferred];
}

export function firstOpenQuizIndex<T extends QuizQuestionRef>(
  deck: T[],
  progress: LearnProgress,
): number {
  const order = buildOpenQuizIndices(deck, progress);
  return order[0] ?? 0;
}

export function nextOpenQuizIndex<T extends QuizQuestionRef>(
  deck: T[],
  progress: LearnProgress,
  currentIndex: number,
): number | null {
  const order = buildOpenQuizIndices(deck, progress);
  const pos = order.indexOf(currentIndex);
  if (pos >= 0 && pos + 1 < order.length) return order[pos + 1] ?? null;
  if (order.length === 0) return null;
  return order.find((idx) => idx !== currentIndex) ?? null;
}

export function countAnsweredInDeck<T extends QuizQuestionRef>(
  deck: T[],
  progress: LearnProgress,
): number {
  return deck.filter((q) => isQuizAnswered(progress, q)).length;
}
