"""Validierung für interaktive Lerntrainer-Module."""

from __future__ import annotations

from app.ai.errors import LlmError


def normalize_question(text: str) -> str:
    return " ".join(
        text.lower()
        .replace("?", "")
        .replace(".", "")
        .replace(",", "")
        .split()
    )


def dedupe_interactive_modules(modules: list) -> tuple[list, list[str]]:
    """Entfernt doppelte Karten-/Quizfragen (behalten: erste). Warnungen statt Abbruch."""
    warnings: list[str] = []
    seen: set[str] = set()

    for index, raw in enumerate(modules):
        if not isinstance(raw, dict):
            continue
        content = raw.get("content") if isinstance(raw.get("content"), dict) else {}
        cards = content.get("cards") if isinstance(content.get("cards"), list) else []
        quiz = raw.get("quiz") if isinstance(raw.get("quiz"), dict) else {}
        questions = quiz.get("questions") if isinstance(quiz.get("questions"), list) else []

        kept_cards: list = []
        for card in cards:
            if not isinstance(card, dict):
                kept_cards.append(card)
                continue
            norm = normalize_question(str(card.get("question") or ""))
            if norm in seen:
                warnings.append(
                    f"Duplikat Lernkarte entfernt (Bereich {index + 1}): {card.get('question')}"
                )
                continue
            seen.add(norm)
            kept_cards.append(card)
        content["cards"] = kept_cards

        kept_questions: list = []
        for q in questions:
            if not isinstance(q, dict):
                kept_questions.append(q)
                continue
            norm = normalize_question(str(q.get("q") or ""))
            if norm in seen:
                warnings.append(
                    f"Duplikat Quizfrage entfernt (Bereich {index + 1}): {q.get('q')}"
                )
                continue
            seen.add(norm)
            kept_questions.append(q)
        quiz["questions"] = kept_questions

    return modules, warnings


def validate_interactive_modules(
    modules: list,
    *,
    min_cards: int,
    min_questions: int,
) -> None:
    if len(modules) < 4:
        raise LlmError(
            f"Zu wenige Themenbereiche ({len(modules)}, mindestens 4)",
            "thin_content",
        )
    total_cards = 0
    total_questions = 0
    seen_questions: set[str] = set()

    for index, raw in enumerate(modules):
        if not isinstance(raw, dict):
            raise LlmError(f"Bereich {index + 1} ungültig", "bad_json")
        content = raw.get("content") if isinstance(raw.get("content"), dict) else {}
        cards = content.get("cards") if isinstance(content.get("cards"), list) else []
        quiz = raw.get("quiz") if isinstance(raw.get("quiz"), dict) else {}
        questions = quiz.get("questions") if isinstance(quiz.get("questions"), list) else []

        total_cards += len(cards)
        total_questions += len(questions)

        for c_index, card in enumerate(cards):
            if not isinstance(card, dict):
                raise LlmError(f"Karte {c_index + 1} in Bereich {index + 1} ungültig", "bad_json")
            if not str(card.get("question") or "").strip():
                raise LlmError(f"Lernkarte ohne Frage (Bereich {index + 1})", "bad_json")
            if not str(card.get("answer") or "").strip():
                raise LlmError(f"Lernkarte ohne Antwort (Bereich {index + 1})", "bad_json")
            norm = normalize_question(str(card.get("question") or ""))
            if norm in seen_questions:
                raise LlmError(f"Doppelte Lernkartenfrage: {card.get('question')}", "thin_content")
            seen_questions.add(norm)

        for q_index, q in enumerate(questions):
            if not isinstance(q, dict):
                raise LlmError(f"Quizfrage {q_index + 1} in Bereich {index + 1} ungültig", "bad_json")
            options = q.get("options") if isinstance(q.get("options"), list) else []
            if len(options) != 4:
                raise LlmError(
                    f"Quizfrage {q_index + 1} in Bereich {index + 1} braucht 4 Optionen",
                    "bad_json",
                )
            norm = normalize_question(str(q.get("q") or ""))
            if norm in seen_questions:
                raise LlmError(f"Doppelte Quizfrage: {q.get('q')}", "thin_content")
            seen_questions.add(norm)

    if total_cards < min_cards:
        raise LlmError(
            f"Zu wenige Lernkarten ({total_cards}, mindestens {min_cards})",
            "thin_content",
        )
    if total_questions < min_questions:
        raise LlmError(
            f"Zu wenige Quizfragen ({total_questions}, mindestens {min_questions})",
            "thin_content",
        )
