"use client";

import { ColumnMulGrid } from "@/components/learn/ColumnMulGrid";
import { extractColumnMul, splitQuizExplanation } from "@/lib/quizOption";

function VariantBody({ text }: { text: string }) {
  const { layout, rest } = extractColumnMul(text);
  return (
    <>
      {layout ? <ColumnMulGrid layout={layout} /> : null}
      {rest ? <p className="muted quiz-explanation-text">{rest}</p> : null}
    </>
  );
}

export function QuizExplanation({ text }: { text: string }) {
  const { preamble, variants } = splitQuizExplanation(text);
  if (!preamble && variants.length === 0) return null;

  const named = /Variante\s+\d+/i.test(text);
  if (!named) {
    return (
      <div className="quiz-explanation">
        {preamble ? <p className="quiz-result-line">{preamble}</p> : null}
        <VariantBody text={variants[0]?.body || ""} />
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
          <VariantBody text={variant.body} />
        </div>
      ))}
    </div>
  );
}
