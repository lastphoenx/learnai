"""Lernziele pro Einheit (Eltern/Admin) und persönliche Ziele (Kind)."""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any, Literal

CARD_KINDS = ("merk", "mental", "input")
CardTarget = int | Literal["all"] | None

_KIND_LABELS = {
    "merk": "Merk-Karten",
    "mental": "Kopf-Karten",
    "input": "Eingabe-Karten",
    "quiz": "Quizfragen",
}


def _normalize_kind(kind: str | None) -> str:
    k = str(kind or "mental").strip().lower()
    return k if k in CARD_KINDS else "mental"


def normalize_card_targets(raw: dict | None) -> dict[str, CardTarget]:
    out: dict[str, CardTarget] = {k: None for k in CARD_KINDS}
    if not isinstance(raw, dict):
        return out
    for kind in CARD_KINDS:
        value = raw.get(kind)
        if value is None or value == "":
            out[kind] = None
        elif isinstance(value, str) and value.strip().lower() == "all":
            out[kind] = "all"
        else:
            try:
                n = int(value)
                out[kind] = n if n > 0 else None
            except (TypeError, ValueError):
                out[kind] = None
    return out


def normalize_learn_goals(raw: dict | None) -> dict[str, Any]:
    data = dict(raw or {})
    quiz_raw = data.get("quiz")
    quiz: int | None
    try:
        quiz = int(quiz_raw) if quiz_raw is not None and int(quiz_raw) > 0 else None
    except (TypeError, ValueError):
        quiz = None
    deadline = data.get("deadline")
    if isinstance(deadline, str) and deadline.strip():
        deadline = deadline.strip()[:10]
    else:
        deadline = None
    return {
        "quiz": quiz,
        "cards": normalize_card_targets(data.get("cards") if isinstance(data.get("cards"), dict) else {}),
        "deadline": deadline,
    }


def resolve_target(target: CardTarget, *, available: int) -> int | None:
    if target is None:
        return None
    if target == "all":
        return available if available > 0 else None
    return int(target)


def count_quiz_answered(learn_modules: dict, modules: list) -> int:
    from app.services.crypto_json import decrypt_json

    total = 0
    for module in modules:
        mod_key = str(module.id)
        mod_prog = learn_modules.get(mod_key)
        if not isinstance(mod_prog, dict):
            continue
        answers = mod_prog.get("answers") or []
        quiz = decrypt_json(module.quiz_encrypted) or {}
        questions = quiz.get("questions") if isinstance(quiz, dict) else []
        if not isinstance(questions, list):
            questions = []
        for i, selected in enumerate(answers):
            if i < len(questions) and selected is not None:
                total += 1
    return total


def count_cards_by_kind(
    modules: list,
    *,
    flashcard_progress: dict[str, dict],
    learn_modules: dict,
) -> dict[str, int]:
    from app.services.crypto_json import decrypt_json

    def _card_key(module_id, card_index: int) -> str:
        return f"{module_id}:{card_index}"

    counts = {k: 0 for k in CARD_KINDS}
    for module in modules:
        content = decrypt_json(module.content_encrypted) or {}
        if not isinstance(content, dict):
            continue
        mod_key = str(module.id)
        mod_prog = learn_modules.get(mod_key) if isinstance(learn_modules.get(mod_key), dict) else {}
        card_inputs = mod_prog.get("card_input_answers") or []
        for index, card in enumerate(content.get("cards") or []):
            if not isinstance(card, dict):
                continue
            kind = _normalize_kind(card.get("kind"))
            if kind == "input":
                entry = card_inputs[index] if index < len(card_inputs) else None
                if isinstance(entry, dict) and entry.get("correct"):
                    counts["input"] += 1
            else:
                key = _card_key(module.id, index)
                status = (flashcard_progress.get(key) or {}).get("status")
                if status in {"known", "review"}:
                    counts[kind] += 1
    return counts


def _item_progress(*, label: str, done: int, target: int | None) -> dict[str, Any]:
    if target is None or target <= 0:
        return {
            "key": label,
            "label": _KIND_LABELS.get(label, label),
            "done": done,
            "target": None,
            "percent": None,
            "met": None,
            "bonus": 0,
            "remaining": None,
            "message": None,
        }
    met = done >= target
    bonus = max(0, done - target)
    remaining = max(0, target - done)
    percent = min(100, round(100 * done / target)) if target else None
    message = motivational_message(label=label, done=done, target=target, bonus=bonus)
    return {
        "key": label,
        "label": _KIND_LABELS.get(label, label),
        "done": done,
        "target": target,
        "percent": percent,
        "met": met,
        "bonus": bonus,
        "remaining": remaining,
        "message": message,
    }


def motivational_message(*, label: str, done: int, target: int, bonus: int) -> str:
    name = _KIND_LABELS.get(label, label)
    if done >= target:
        if bonus > 0:
            return f"Klasse! {bonus} {name} über dem Ziel — weiter so!"
        return f"Ziel erreicht: {name}!"
    remaining = target - done
    if done == 0:
        return f"Los geht's — noch {remaining} {name} bis zum Ziel."
    if done >= target * 0.75:
        return f"Fast geschafft — nur noch {remaining} {name}!"
    return f"Gut dran: {done} von {target} {name}."


def build_goals_progress(
    goals: dict | None,
    *,
    quiz_done: int,
    card_done: dict[str, int],
    card_available: dict[str, int],
    source: str = "parent",
) -> dict[str, Any]:
    normalized = normalize_learn_goals(goals)
    items: list[dict[str, Any]] = []

    quiz_target = normalized.get("quiz")
    if isinstance(quiz_target, int) and quiz_target > 0:
        items.append(_item_progress(label="quiz", done=quiz_done, target=quiz_target))

    for kind in CARD_KINDS:
        raw_target = normalized.get("cards", {}).get(kind)
        target = resolve_target(raw_target, available=card_available.get(kind, 0))
        if target is not None:
            items.append(_item_progress(label=kind, done=card_done.get(kind, 0), target=target))

    deadline = normalized.get("deadline")
    days_left: int | None = None
    overdue = False
    if deadline:
        try:
            due = date.fromisoformat(str(deadline))
            days_left = (due - date.today()).days
            overdue = days_left < 0
        except ValueError:
            deadline = None

    active = [i for i in items if i.get("target")]
    met_count = sum(1 for i in active if i.get("met"))
    overall_percent = round(100 * met_count / len(active)) if active else None
    headline = None
    if active and met_count == len(active):
        headline = "Alle Ziele erreicht — toll gemacht!"
    elif overdue and active and met_count < len(active):
        headline = "Das Zieldatum ist vorbei — trotzdem weiter üben!"
    elif days_left is not None and 0 <= days_left <= 3 and met_count < len(active):
        headline = f"Noch {days_left} Tag{'e' if days_left != 1 else ''} bis zum Ziel."

    return {
        "source": source,
        "quiz": normalized.get("quiz"),
        "cards": normalized.get("cards"),
        "deadline": deadline,
        "days_left": days_left,
        "overdue": overdue,
        "items": items,
        "met_count": met_count,
        "active_count": len(active),
        "overall_percent": overall_percent,
        "headline": headline,
    }


def merge_goals_payload(
    *,
    parent_goals: dict | None,
    child_goals: dict | None,
    quiz_done: int,
    card_done: dict[str, int],
    card_available: dict[str, int],
) -> dict[str, Any]:
    parent = build_goals_progress(
        parent_goals,
        quiz_done=quiz_done,
        card_done=card_done,
        card_available=card_available,
        source="parent",
    )
    child = build_goals_progress(
        child_goals,
        quiz_done=quiz_done,
        card_done=card_done,
        card_available=card_available,
        source="child",
    )
    return {
        "parent": parent,
        "child": child,
        "quiz_done": quiz_done,
        "card_done": card_done,
        "card_available": card_available,
    }
