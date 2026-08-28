import { describe, expect, it } from "vitest";

import type { LearnProgress } from "@/lib/api";
import { getStoredQuizAnswer } from "@/lib/quizNav";
import {
  formatAttemptSuccessLabel,
  isQuizRetryable,
  quizAnswerGradientStyle,
  quizAnswerMixDangerPercent,
  quizRetryCooldownRemainingMs,
} from "@/lib/quizRetry";

const progress = {
  status: "in_progress",
  module_index: 0,
  phase: "quiz",
  question_index: 0,
  modules: {
    mod1: {
      answers: [1],
      answer_details: {
        "0": {
          selected: 1,
          correct: false,
          correct_index: 0,
          retry_available_at: new Date(Date.now() + 5 * 60_000).toISOString(),
        },
      },
    },
  },
  quiz_correct: 0,
  quiz_total: 1,
  started_at: null,
  completed_at: null,
} satisfies LearnProgress;

describe("quizRetry", () => {
  it("blocks retry during cooldown", () => {
    const q = { module_id: "mod1", question_index: 0 };
    expect(isQuizRetryable(progress, q)).toBe(false);
    const stored = getStoredQuizAnswer(progress, q);
    expect(quizRetryCooldownRemainingMs(stored)).toBeGreaterThan(0);
  });

  it("allows retry after cooldown", () => {
    const q = { module_id: "mod1", question_index: 0 };
    const past = {
      ...progress,
      modules: {
        mod1: {
          answers: [1],
          answer_details: {
            "0": {
              selected: 1,
              correct: false,
              correct_index: 0,
              retry_available_at: new Date(Date.now() - 60_000).toISOString(),
            },
          },
        },
      },
    } satisfies LearnProgress;
    expect(isQuizRetryable(past, q)).toBe(true);
  });

  it("mixes more red with more attempts", () => {
    expect(quizAnswerMixDangerPercent(1, true)).toBeNull();
    expect(quizAnswerMixDangerPercent(2, true)).toBe(50);
    expect(quizAnswerMixDangerPercent(3, true)).toBe(67);
  });

  it("formats attempt success label", () => {
    expect(formatAttemptSuccessLabel(1)).toBeNull();
    expect(formatAttemptSuccessLabel(2)).toBe("Richtig — beim 2. Versuch");
  });

  it("returns gradient style for multi-attempt success", () => {
    const style = quizAnswerGradientStyle({
      selected: 0,
      correct: true,
      correct_index: 0,
      attempts: 2,
    });
    expect(style?.borderColor).toContain("color-mix");
  });
});
