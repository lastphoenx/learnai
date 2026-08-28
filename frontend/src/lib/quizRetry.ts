import type { CSSProperties } from "react";

import type { LearnProgress } from "@/lib/api";
import { getStoredQuizAnswer, type QuizQuestionRef, type StoredQuizAnswer } from "@/lib/quizNav";

export function quizRetryAvailableAt(stored: StoredQuizAnswer | null): Date | null {
  if (!stored?.retry_available_at) return null;
  const parsed = new Date(stored.retry_available_at);
  return Number.isNaN(parsed.getTime()) ? null : parsed;
}

export function quizRetryCooldownRemainingMs(
  stored: StoredQuizAnswer | null,
  now = Date.now(),
): number {
  const availableAt = quizRetryAvailableAt(stored);
  if (!availableAt) return 0;
  return Math.max(0, availableAt.getTime() - now);
}

export function isQuizRetryable(
  progress: LearnProgress,
  q: QuizQuestionRef,
  now = Date.now(),
): boolean {
  const stored = getStoredQuizAnswer(progress, q);
  if (!stored || stored.correct) return false;
  return quizRetryCooldownRemainingMs(stored, now) <= 0;
}

export function isQuizRetryPending(
  progress: LearnProgress,
  q: QuizQuestionRef,
  now = Date.now(),
): boolean {
  const stored = getStoredQuizAnswer(progress, q);
  if (!stored || stored.correct) return false;
  return quizRetryCooldownRemainingMs(stored, now) > 0;
}

export function buildRetryQuizIndices<T extends QuizQuestionRef>(
  deck: T[],
  progress: LearnProgress,
  now = Date.now(),
): number[] {
  return deck
    .map((q, index) => (isQuizRetryable(progress, q, now) ? index : -1))
    .filter((index) => index >= 0);
}

export function nextRetryQuizIndex<T extends QuizQuestionRef>(
  deck: T[],
  progress: LearnProgress,
  currentIndex: number,
  now = Date.now(),
): number | null {
  const order = buildRetryQuizIndices(deck, progress, now);
  const pos = order.indexOf(currentIndex);
  if (pos >= 0 && pos + 1 < order.length) return order[pos + 1] ?? null;
  return order.find((idx) => idx !== currentIndex) ?? null;
}

export function quizAnswerMixDangerPercent(attempts: number, correct: boolean): number | null {
  if (!correct) return null;
  const count = attempts || 1;
  if (count <= 1) return null;
  return Math.round(((count - 1) / count) * 100);
}

export function quizAnswerGradientStyle(
  stored: StoredQuizAnswer | null,
): CSSProperties | undefined {
  if (!stored?.correct) return undefined;
  const mix = quizAnswerMixDangerPercent(stored.attempts ?? 1, stored.correct);
  if (mix == null || mix <= 0) return undefined;
  return {
    borderColor: `color-mix(in srgb, var(--danger) ${mix}%, var(--accent))`,
    background: `color-mix(in srgb, var(--danger) ${Math.max(8, Math.round(mix * 0.14))}%, var(--card))`,
  };
}

export function formatRetryCooldown(ms: number): string {
  if (ms <= 0) return "";
  const totalMinutes = Math.ceil(ms / 60_000);
  if (totalMinutes >= 60) {
    const hours = Math.floor(totalMinutes / 60);
    const minutes = totalMinutes % 60;
    return minutes > 0 ? `${hours} Std. ${minutes} Min.` : `${hours} Std.`;
  }
  return `${totalMinutes} Min.`;
}

export function formatAttemptSuccessLabel(attempts: number): string | null {
  if (attempts <= 1) return null;
  return `Richtig — beim ${attempts}. Versuch`;
}
