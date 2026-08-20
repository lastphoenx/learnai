"""Ollama-Modellnamen anhand von Katalog-Hints auflösen (Reihenfolge = Priorität)."""

from __future__ import annotations


def _matches_hint(installed: str, hint: str) -> bool:
    h = hint.strip().lower()
    if not h:
        return False
    lower = installed.lower()
    if lower == h:
        return True
    if ":" in h:
        return lower == h
    token = h.split(":")[0]
    return lower.startswith(f"{token}:") or lower.startswith(f"{token}-")


def match_ollama_hints(hints: list[str], installed: list[str], *, limit: int = 3) -> list[str]:
    """Bis zu `limit` installierte Modelle, in Hint-Reihenfolge (1. = beste Wahl)."""
    picked: list[str] = []
    used: set[str] = set()
    for hint in hints:
        if len(picked) >= limit:
            break
        for name in installed:
            if name in used:
                continue
            if _matches_hint(name, hint):
                picked.append(name)
                used.add(name)
                break
    return picked


def first_ollama_hint(hints: list[str], installed: list[str]) -> str:
    matched = match_ollama_hints(hints, installed, limit=1)
    return matched[0] if matched else ""
