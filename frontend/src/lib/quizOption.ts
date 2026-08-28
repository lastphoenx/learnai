/** Einheitliche Anzeige für Quiz-Optionen (ohne doppeltes a) A)). */
import type { CSSProperties } from "react";

import { quizAnswerGradientStyle } from "@/lib/quizRetry";
import type { StoredQuizAnswer } from "@/lib/quizNav";
export function formatQuizOption(option: string, index: number): string {
  const label = option.replace(/^[a-d]\)\s*/i, "").trim();
  const letter = String.fromCharCode(65 + index);
  return `${letter}) ${label}`;
}

/** Zeilenumbrüche zwischen Rechenweg-Varianten sichtbar machen. */
export function formatQuizExplanation(text: string): string {
  return text
    .replace(/(=\s*-?\d+(?:[.,]\d+)?)\s*,\s*(?=-?\d+(?:[.,]\d+)?\s*[·×*+\-−:÷/])/g, "$1.\nDann ")
    .replace(/\. Variante /g, ".\n\nVariante ")
    .replace(/ (?=Variante [2-9])/g, "\n\n");
}

export type QuizExplanationVariant = {
  index: number;
  label: string;
  badge: "heft" | "alt";
  body: string;
};

export type ColumnMulLayout = {
  kind: "column_mul";
  top: string;
  bottom: string;
  carries: string[];
  partials: string[];
  total: string;
  decimals: number;
  result: string;
};

const VARIANT_HEAD = /Variante\s+(\d+)\s*(?:\(([^)]*)\))?\s*:/gi;
const COLUMN_MUL_MARK = /<<spalten:(\{[\s\S]*?\})>>/;

export function extractColumnMul(text: string): { layout: ColumnMulLayout | null; rest: string } {
  const src = text || "";
  const match = src.match(COLUMN_MUL_MARK);
  if (!match) return { layout: null, rest: src.trim() };
  try {
    const parsed = JSON.parse(match[1]) as ColumnMulLayout;
    if (parsed?.kind !== "column_mul" || !parsed.top || !parsed.bottom) {
      return { layout: null, rest: src.trim() };
    }
    const rest = `${src.slice(0, match.index ?? 0)}${src.slice((match.index ?? 0) + match[0].length)}`;
    return { layout: parsed, rest: rest.replace(/\s+/g, " ").trim() };
  } catch {
    return { layout: null, rest: src.trim() };
  }
}

export function splitQuizExplanation(text: string): {
  preamble: string;
  variants: QuizExplanationVariant[];
} {
  const src = formatQuizExplanation(text || "").trim();
  if (!src) return { preamble: "", variants: [] };
  const ergebnis = src.match(/^Ergebnis:\s*(.+)(?:\n+|$)/i);
  const preambleFromResult = ergebnis ? `Ergebnis: ${ergebnis[1].trim()}` : "";
  const rest = ergebnis ? src.slice(ergebnis[0].length).trim() : src;
  const matches = [...rest.matchAll(new RegExp(VARIANT_HEAD.source, "gi"))];
  if (matches.length === 0) {
    return {
      preamble: preambleFromResult,
      variants: rest ? [{ index: 1, label: "", badge: "heft", body: rest }] : [],
    };
  }
  const preamble = [preambleFromResult, rest.slice(0, matches[0].index ?? 0).trim()]
    .filter(Boolean)
    .join("\n\n");
  const variants: QuizExplanationVariant[] = matches.map((match, i) => {
    const start = (match.index ?? 0) + match[0].length;
    const end = i + 1 < matches.length ? (matches[i + 1].index ?? rest.length) : rest.length;
    return {
      index: Number(match[1]),
      label: (match[2] || "").trim(),
      badge: (i === 0 ? "heft" : "alt") as QuizExplanationVariant["badge"],
      body: rest.slice(start, end).trim(),
    };
  });
  return { preamble, variants };
}

export function splitQuizExplanationVariants(text: string): QuizExplanationVariant[] {
  return splitQuizExplanation(text).variants;
}

export function quizOptionClassName(
  index: number,
  selected: number | null,
  answerResult: { correct: boolean; correct_index: number; attempts?: number } | null,
): string {
  let cls = "learn-quiz-option";
  if (!answerResult) {
    if (selected === index) cls += " selected";
    return cls;
  }
  if (selected === index) cls += " picked";
  if (selected === index) {
    if (answerResult.correct) {
      const attempts = answerResult.attempts ?? 1;
      cls += attempts > 1 ? " correct-retry" : " correct";
    } else {
      cls += " wrong";
    }
  } else if (!answerResult.correct && index === answerResult.correct_index) {
    cls += " correct";
  }
  return cls;
}

export function quizOptionStyle(
  index: number,
  selected: number | null,
  answerResult: { correct: boolean; correct_index: number; attempts?: number } | null,
  stored?: StoredQuizAnswer | null,
): CSSProperties | undefined {
  if (!answerResult || selected !== index || !answerResult.correct) return undefined;
  return quizAnswerGradientStyle(
    stored ?? {
      selected: index,
      correct: true,
      correct_index: answerResult.correct_index,
      attempts: answerResult.attempts ?? 1,
    },
  );
}
