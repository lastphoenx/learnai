"""Quiz-Antwortoptionen zufällig mischen (gegen LLM-Bias auf Index 0)."""

from __future__ import annotations

import random


def shuffle_quiz_question(question: dict) -> dict:
    """Gibt eine Kopie mit gemischten options und angepasstem answer-Index zurück."""
    if not isinstance(question, dict):
        return question
    options = question.get("options")
    if not isinstance(options, list) or len(options) != 4:
        return dict(question)
    try:
        answer = int(question.get("answer", -1))
    except (TypeError, ValueError):
        return dict(question)
    if answer < 0 or answer > 3:
        return dict(question)

    indexed = list(enumerate(options))
    random.shuffle(indexed)
    new_options = [opt for _, opt in indexed]
    new_answer = next(i for i, (orig_i, _) in enumerate(indexed) if orig_i == answer)

    out = dict(question)
    out["options"] = new_options
    out["answer"] = new_answer
    return out


def shuffle_quiz_questions(questions: list) -> list:
    if not isinstance(questions, list):
        return questions
    return [shuffle_quiz_question(q) for q in questions]


def shuffle_quiz_block(quiz: dict | None) -> dict:
    if not isinstance(quiz, dict):
        return {"questions": []}
    out = dict(quiz)
    questions = quiz.get("questions")
    if isinstance(questions, list):
        out["questions"] = shuffle_quiz_questions(questions)
    return out
