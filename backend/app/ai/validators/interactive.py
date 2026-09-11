"""Validierung für interaktive Lerntrainer-Module."""

from __future__ import annotations

import re

from app.ai.errors import LlmError
from app.core.basiswissen import is_weak_mental_card_entry, mental_term_from_question
from app.core.quiz_numeric import parse_quiz_numeric, resolve_quiz_expected_value

_IMPORT_TERM = re.compile(r"«([^»]+)»")

IMPORT_MAX_MODULES = 8
IMPORT_MAX_CARDS = 150
IMPORT_MAX_QUESTIONS = 150
IMPORT_MAX_KNOWLEDGE = 30


def normalize_question(text: str) -> str:
    return " ".join(
        text.lower()
        .replace("?", "")
        .replace(".", "")
        .replace(",", "")
        .split()
    )


def parse_quiz_answer(raw: dict, *, label: str = "Quizfrage") -> int:
    value = raw.get("answer", 0)
    if isinstance(value, bool):
        raise LlmError(f"{label}: answer muss 0–3 sein", "bad_json")
    if isinstance(value, int):
        answer = value
    elif isinstance(value, float) and value.is_integer():
        answer = int(value)
    elif isinstance(value, str) and value.strip().isdigit():
        answer = int(value.strip())
    else:
        raise LlmError(f"{label}: answer muss 0–3 sein", "bad_json")
    if answer < 0 or answer > 3:
        raise LlmError(f"{label}: answer muss 0–3 sein", "bad_json")
    return answer


def _validate_card_item(card: dict, c_index: int, area_index: int) -> None:
    if not isinstance(card, dict):
        raise LlmError(f"Karte {c_index + 1} in Bereich {area_index + 1} ungültig", "bad_json")
    if not str(card.get("question") or "").strip():
        raise LlmError(f"Lernkarte ohne Frage (Bereich {area_index + 1})", "bad_json")
    if not str(card.get("answer") or "").strip():
        raise LlmError(f"Lernkarte ohne Antwort (Bereich {area_index + 1})", "bad_json")


def _validate_quiz_item(q: dict, q_index: int, area_index: int) -> None:
    if not isinstance(q, dict):
        raise LlmError(f"Quizfrage {q_index + 1} in Bereich {area_index + 1} ungültig", "bad_json")
    label = f"Quizfrage {q_index + 1} in Bereich {area_index + 1}"
    if not str(q.get("q") or "").strip():
        raise LlmError(f"{label}: Frage fehlt", "bad_json")
    options = q.get("options") if isinstance(q.get("options"), list) else []
    if len(options) != 4:
        raise LlmError(f"{label} braucht 4 Optionen", "bad_json")
    normalized_opts: list[str] = []
    for opt in options:
        text = str(opt or "").strip()
        if not text:
            raise LlmError(f"{label}: leere Antwortoption", "bad_json")
        normalized_opts.append(text.lower())
    if len(set(normalized_opts)) < 4:
        raise LlmError(f"{label}: Antwortoptionen müssen verschieden sein", "bad_json")
    numeric_values: list[float] = []
    for opt in options:
        parsed = parse_quiz_numeric(str(opt))
        if parsed is not None:
            numeric_values.append(parsed)
    for i, left in enumerate(numeric_values):
        for right in numeric_values[i + 1 :]:
            if abs(left - right) < 1e-6:
                raise LlmError(
                    f"{label}: Antwortoptionen müssen auch numerisch verschieden sein",
                    "bad_json",
                )
    parse_quiz_answer(q, label=label)
    q_type = str(q.get("question_type") or "calculation").strip().lower()
    if q_type == "concept":
        return
    expected = resolve_quiz_expected_value(q)
    if expected is not None:
        answer_idx = int(q.get("answer", -1))
        answer_val = parse_quiz_numeric(str(options[answer_idx]))
        if answer_val is None or abs(answer_val - expected) >= 1e-6:
            raise LlmError(f"{label}: answer passt nicht zur Erklärung oder Aufgabe", "bad_json")


def validate_interactive_structure(
    modules: list,
    *,
    max_modules: int = IMPORT_MAX_MODULES,
    max_cards_total: int | None = None,
    max_questions_total: int | None = None,
    max_knowledge_per_module: int = IMPORT_MAX_KNOWLEDGE,
) -> None:
    if len(modules) > max_modules:
        raise LlmError(f"Zu viele Bereiche ({len(modules)}, max. {max_modules})", "bad_json")
    total_cards = 0
    total_questions = 0
    for index, raw in enumerate(modules):
        if not isinstance(raw, dict):
            raise LlmError(f"Bereich {index + 1} ungültig", "bad_json")
        content = raw.get("content") if isinstance(raw.get("content"), dict) else {}
        cards = content.get("cards") if isinstance(content.get("cards"), list) else []
        quiz = raw.get("quiz") if isinstance(raw.get("quiz"), dict) else {}
        questions = quiz.get("questions") if isinstance(quiz.get("questions"), list) else []
        knowledge = content.get("knowledge") if isinstance(content.get("knowledge"), list) else []
        if len(knowledge) > max_knowledge_per_module:
            raise LlmError(
                f"Bereich {index + 1}: zu viele Wissens-Einträge (max. {max_knowledge_per_module})",
                "bad_json",
            )
        for c_index, card in enumerate(cards):
            _validate_card_item(card, c_index, index)
        for q_index, q in enumerate(questions):
            _validate_quiz_item(q, q_index, index)
        total_cards += len(cards)
        total_questions += len(questions)
    if max_cards_total is not None and total_cards > max_cards_total:
        raise LlmError(f"Zu viele Lernkarten ({total_cards}, max. {max_cards_total})", "bad_json")
    if max_questions_total is not None and total_questions > max_questions_total:
        raise LlmError(f"Zu viele Quizfragen ({total_questions}, max. {max_questions_total})", "bad_json")


def dedupe_interactive_modules(modules: list) -> tuple[list, list[str]]:
    """Entfernt doppelte Karten-/Quizfragen (behalten: erste). Warnungen statt Abbruch."""
    warnings: list[str] = []
    seen: set[str] = set()
    seen_terms: set[str] = set()

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
            term_match = _IMPORT_TERM.search(str(card.get("question") or ""))
            term_key = term_match.group(1).strip().lower() if term_match else ""
            if term_key and term_key in seen_terms:
                warnings.append(
                    f"Duplikat-Begriff entfernt (Bereich {index + 1}): {card.get('question')}"
                )
                continue
            if norm in seen:
                warnings.append(
                    f"Duplikat Lernkarte entfernt (Bereich {index + 1}): {card.get('question')}"
                )
                continue
            seen.add(norm)
            if term_key:
                seen_terms.add(term_key)
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


def sanitize_interactive_modules(modules: list) -> tuple[list, list[str]]:
    """Entfernt schwache Mental-Karten (tautologisch/leer) aus allen Modulen."""
    warnings: list[str] = []
    for index, raw in enumerate(modules):
        if not isinstance(raw, dict):
            continue
        content = raw.get("content") if isinstance(raw.get("content"), dict) else {}
        cards = content.get("cards") if isinstance(content.get("cards"), list) else []
        kept_cards: list = []
        for card in cards:
            if not isinstance(card, dict):
                kept_cards.append(card)
                continue
            kind = str(card.get("kind") or "").strip().lower()
            question = str(card.get("question") or "").strip()
            answer = str(card.get("answer") or "").strip()
            is_mental = kind == "mental" or "was bedeutet «" in question.lower()
            if not is_mental:
                kept_cards.append(card)
                continue
            term = mental_term_from_question(question)
            if term and is_weak_mental_card_entry(question=question, answer=answer, term=term):
                warnings.append(
                    f"Schwache Mental-Karte entfernt (Bereich {index + 1}): {question[:120]}"
                )
                continue
            kept_cards.append(card)
        content["cards"] = kept_cards
    return modules, warnings


def trim_interactive_modules_to_budget(
    modules: list,
    *,
    max_cards: int | None = None,
    max_questions: int | None = None,
    min_cards_per_module: int = 1,
    min_questions_per_module: int = 0,
) -> list:
    """Kürzt Module auf Preset-Obergrenze — bevorzugt reichere Module, Mindestanzahl pro Modul."""
    if not modules:
        return modules
    if max_cards is None and max_questions is None:
        return modules

    def totals() -> tuple[int, int]:
        cards = 0
        questions = 0
        for raw in modules:
            if not isinstance(raw, dict):
                continue
            content = raw.get("content") if isinstance(raw.get("content"), dict) else {}
            quiz = raw.get("quiz") if isinstance(raw.get("quiz"), dict) else {}
            cards += len(content.get("cards") or [])
            questions += len(quiz.get("questions") or [])
        return cards, questions

    total_cards, total_questions = totals()
    if (max_cards is None or total_cards <= max_cards) and (
        max_questions is None or total_questions <= max_questions
    ):
        return modules

    while True:
        total_cards, total_questions = totals()
        if max_cards is not None and total_cards <= max_cards and (
            max_questions is None or total_questions <= max_questions
        ):
            break
        if max_questions is not None and total_questions <= max_questions and (
            max_cards is None or total_cards <= max_cards
        ):
            break

        trimmed = False
        if max_cards is not None and total_cards > max_cards:
            best_index: int | None = None
            best_count = min_cards_per_module
            for index, raw in enumerate(modules):
                if not isinstance(raw, dict):
                    continue
                content = raw.get("content") if isinstance(raw.get("content"), dict) else {}
                cards = content.get("cards") if isinstance(content.get("cards"), list) else []
                if len(cards) > best_count:
                    best_count = len(cards)
                    best_index = index
            if best_index is not None:
                raw = modules[best_index]
                content = raw.get("content") if isinstance(raw.get("content"), dict) else {}
                cards = content.get("cards") if isinstance(content.get("cards"), list) else []
                cards.pop()
                content["cards"] = cards
                trimmed = True

        total_cards, total_questions = totals()
        if max_questions is not None and total_questions > max_questions:
            best_q_index: int | None = None
            best_q_count = min_questions_per_module
            for index, raw in enumerate(modules):
                if not isinstance(raw, dict):
                    continue
                quiz = raw.get("quiz") if isinstance(raw.get("quiz"), dict) else {}
                questions = quiz.get("questions") if isinstance(quiz.get("questions"), list) else []
                if len(questions) > best_q_count:
                    best_q_count = len(questions)
                    best_q_index = index
            if best_q_index is not None:
                raw = modules[best_q_index]
                quiz = raw.get("quiz") if isinstance(raw.get("quiz"), dict) else {}
                questions = quiz.get("questions") if isinstance(quiz.get("questions"), list) else []
                questions.pop()
                quiz["questions"] = questions
                trimmed = True

        if not trimmed:
            break
    return modules


def validate_interactive_modules(
    modules: list,
    *,
    min_cards: int,
    min_questions: int,
    min_modules: int = 4,
) -> None:
    validate_interactive_structure(modules)
    if len(modules) < min_modules:
        raise LlmError(
            f"Zu wenige Themenbereiche ({len(modules)}, mindestens {min_modules})",
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

        for card in cards:
            if not isinstance(card, dict):
                continue
            norm = normalize_question(str(card.get("question") or ""))
            if norm in seen_questions:
                raise LlmError(f"Doppelte Lernkartenfrage: {card.get('question')}", "thin_content")
            seen_questions.add(norm)

        for q in questions:
            if not isinstance(q, dict):
                continue
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


def validate_interactive_import(modules: list) -> None:
    """Import: gleiche Struktur wie KI-Output, mit Import-Obergrenzen."""
    validate_interactive_structure(
        modules,
        max_modules=IMPORT_MAX_MODULES,
        max_cards_total=IMPORT_MAX_CARDS,
        max_questions_total=IMPORT_MAX_QUESTIONS,
    )
    if not modules:
        raise LlmError("Keine Module im Import", "bad_json")
