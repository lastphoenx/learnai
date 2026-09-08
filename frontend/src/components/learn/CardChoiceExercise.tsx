"use client";

import { useState } from "react";
import { QuizExplanation } from "@/components/learn/QuizExplanation";
import { answerWithVisibleResult } from "@/lib/cardResult";
import { formatChoiceQuestion } from "@/lib/cardChoices";
import { renderCardQuestion } from "@/lib/cardQuestion";

type Props = {
  question: string;
  choices: string[];
  busy: boolean;
  result: {
    correct: boolean;
    explanation?: string | null;
    expected?: string | null;
  } | null;
  onSubmit: (answer: string) => void;
};

export function CardChoiceExercise({ question, choices, busy, result, onSubmit }: Props) {
  const [selected, setSelected] = useState<string | null>(null);
  const displayQuestion = formatChoiceQuestion(question);

  return (
    <div className="card-choice-exercise stack">
      <p className="learn-quiz-question">{renderCardQuestion(displayQuestion)}</p>
      <div className="learn-quiz-options" role="list">
        {choices.map((choice) => {
          let cls = "learn-quiz-option";
          if (result && selected === choice) {
            cls += result.correct ? " correct picked" : " wrong picked";
          } else if (result && !result.correct && result.expected === choice) {
            cls += " correct";
          }
          return (
            <button
              key={choice}
              type="button"
              className={cls}
              disabled={busy || Boolean(result)}
              onClick={() => {
                setSelected(choice);
                onSubmit(choice);
              }}
            >
              {choice}
            </button>
          );
        })}
      </div>
      {result && (
        <div className="quiz-answer-block">
          <p className={result.correct ? "quiz-verdict ok" : "quiz-verdict bad"}>
            {result.correct ? "Richtig!" : "Noch nicht ganz."}
          </p>
          {result.explanation && (
            <QuizExplanation text={answerWithVisibleResult(question, result.explanation)} />
          )}
          {!result.correct && result.expected && (
            <p className="muted">Lösung: {result.expected}</p>
          )}
        </div>
      )}
    </div>
  );
}
