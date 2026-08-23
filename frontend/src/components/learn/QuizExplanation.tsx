"use client";

import { splitQuizExplanation } from "@/lib/quizOption";

export function QuizExplanation({ text }: { text: string }) {
  const { preamble, variants } = splitQuizExplanation(text);
  if (!preamble && variants.length === 0) return null;

  const named = /Variante\s+\d+/i.test(text);
  if (!named) {
    return (
      <div className="quiz-explanation">
        {preamble ? <p className="quiz-result-line">{preamble}</p> : null}
        <p className="muted quiz-explanation-text">{variants[0]?.body}</p>
      </div>
    );
  }

  return (
    <div className="quiz-explanation-variants">
      {preamble ? <p className="quiz-result-line">{preamble}</p> : null}
      {variants.map((variant) => (
        <div key={variant.index} className="quiz-variant-line">
          <div className="quiz-variant-head">
            <span className={`badge ${variant.badge === "heft" ? "badge-ready" : "badge-neutral"}`}>
              {variant.badge === "heft" ? "Aus dem Heft" : "Alternativer Weg"}
            </span>
            <span className="quiz-variant-title">
              Variante {variant.index}
              {variant.label ? ` (${variant.label})` : ""}
            </span>
          </div>
          <p className="muted quiz-explanation-text">{variant.body}</p>
        </div>
      ))}
    </div>
  );
}
