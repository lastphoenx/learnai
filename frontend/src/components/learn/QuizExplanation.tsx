"use client";

import { splitQuizExplanationVariants } from "@/lib/quizOption";

export function QuizExplanation({ text }: { text: string }) {
  const variants = splitQuizExplanationVariants(text);
  if (variants.length === 0) return null;

  const named = /Variante\s+\d+/i.test(text);
  if (!named) {
    return <p className="muted quiz-explanation-text">{variants[0].body}</p>;
  }

  return (
    <div className="quiz-explanation-variants">
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
