"""Aufgaben-Modul für kompakte Lerntrainer — Timeline oder Quiz-Fallback."""

from __future__ import annotations

from typing import Any

from app.core.basiswissen import empty_basiswissen

_COMPACT_AUFGABEN_TITLE = "Aufgaben"
_DEFAULT_PRACTICE_FROM_QUIZ = 4


def quiz_questions_to_practice_items(
    questions: list[dict],
    *,
    max_count: int = _DEFAULT_PRACTICE_FROM_QUIZ,
    source: str = "posten_compact",
) -> list[dict]:
    """Wandelt MC-Quizfragen in prüfbare Choice-Übungen für den Aufgaben-Tab."""
    items: list[dict] = []
    seen_prompts: set[str] = set()
    for raw in questions:
        if len(items) >= max_count:
            break
        if not isinstance(raw, dict):
            continue
        prompt = str(raw.get("q") or raw.get("question") or "").strip()
        key = prompt.lower()
        if not prompt or key in seen_prompts:
            continue
        options = [str(o).strip() for o in (raw.get("options") or []) if str(o).strip()]
        if len(options) < 2:
            continue
        try:
            answer_idx = int(raw.get("answer", -1))
        except (TypeError, ValueError):
            continue
        if answer_idx < 0 or answer_idx >= len(options):
            continue
        hint = str(raw.get("explanation") or "").strip()[:300] or None
        seen_prompts.add(key)
        items.append(
            {
                "prompt": prompt[:500],
                "hint": hint,
                "answer_type": "choice",
                "options": options[:4],
                "answer": str(answer_idx),
                "source": source,
            }
        )
    return items


def ensure_compact_aufgaben_module(
    modules: list[dict],
    *,
    focus_group: str,
    quiz_source: str = "posten_compact",
    extra_practice: list[dict] | None = None,
    max_quiz_practice: int = _DEFAULT_PRACTICE_FROM_QUIZ,
) -> list[dict]:
    """Practice im Aufgaben-Modul bündeln; ohne Timeline aus Quiz ableiten."""
    if not modules:
        return modules

    collected: list[dict] = []
    seen_prompts: set[str] = set()
    quiz_questions: list[dict] = []

    def add_item(item: dict[str, Any]) -> None:
        prompt = str(item.get("prompt") or "").strip()
        key = prompt.lower()
        if not prompt or key in seen_prompts:
            return
        seen_prompts.add(key)
        collected.append(item)

    for item in extra_practice or []:
        if isinstance(item, dict):
            add_item(dict(item))

    for raw in modules:
        if not isinstance(raw, dict):
            continue
        title = str(raw.get("title") or "").strip()
        content = dict(raw.get("content") or {}) if isinstance(raw.get("content"), dict) else {}
        if title == "Quiz":
            quiz = raw.get("quiz") if isinstance(raw.get("quiz"), dict) else {}
            quiz_questions = [q for q in (quiz.get("questions") or []) if isinstance(q, dict)]
        for item in content.get("practice") or []:
            if isinstance(item, dict):
                add_item(dict(item))
        content["practice"] = []
        raw["content"] = content

    if not collected and quiz_questions:
        for item in quiz_questions_to_practice_items(
            quiz_questions,
            max_count=max_quiz_practice,
            source=quiz_source,
        ):
            add_item(item)

    if not collected:
        return modules

    has_timeline = any(str(i.get("answer_type") or "") == "label_diagram" for i in collected)
    intro = (
        "Ordne Begriffe am Zeitstrahl zu."
        if has_timeline
        else "Prüfbare Wissensaufgaben — wähle die passende Antwort."
    )

    aufgaben_mod = {
        "title": _COMPACT_AUFGABEN_TITLE,
        "content": {
            "intro": intro,
            "knowledge": [],
            "cards": [],
            "practice": collected,
            "basiswissen": empty_basiswissen(focus_group=focus_group),
        },
        "quiz": {"questions": []},
    }

    aufgaben_idx: int | None = None
    for index, raw in enumerate(modules):
        if isinstance(raw, dict) and str(raw.get("title") or "").strip() == _COMPACT_AUFGABEN_TITLE:
            aufgaben_idx = index
            break

    if aufgaben_idx is not None:
        modules[aufgaben_idx] = aufgaben_mod
    else:
        modules.append(aufgaben_mod)
    return modules
