"""Hilfsfunktionen für Trainer-Kartenfilter (Frontend-parität)."""

from __future__ import annotations

from typing import Any


def is_term_trainer_card(card: dict[str, Any]) -> bool:
    """Entspricht `isTermCard` in InteractiveTrainer.tsx — Eingabe-Lücken separat unter «Eingabe»."""
    if str(card.get("kind") or "") == "input":
        return False
    role = str(card.get("card_role") or "")
    if role in {"term", "cloze"}:
        return True
    if str(card.get("source") or "") == "basiswissen":
        return True
    return str(card.get("answer_type") or "") == "cloze"


def card_kind_name(card: dict[str, Any]) -> str:
    kind = str(card.get("kind") or "").strip()
    return kind if kind else "mental"


def count_trainer_card_kinds(cards: list[dict[str, Any]]) -> dict[str, int]:
    merk = mental = input_count = term = 0
    for card in cards:
        kind = card_kind_name(card)
        if kind == "merk":
            merk += 1
        elif kind == "input":
            input_count += 1
        else:
            mental += 1
        if is_term_trainer_card(card):
            term += 1
    return {
        "merk": merk,
        "mental": mental,
        "input": input_count,
        "term": term,
        "all": len(cards),
    }
