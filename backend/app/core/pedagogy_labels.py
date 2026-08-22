"""Material-first Didaktik: Freitext-Labels aus dem Heft sind primär, Taxonomie optional."""

from __future__ import annotations

import re
import unicodedata

from app.core.method_taxonomy import METHOD_LABELS, classify_method, normalize_method_id

_STOPWORDS = frozenset(
    {
        "a",
        "an",
        "am",
        "als",
        "auf",
        "aus",
        "bei",
        "das",
        "dem",
        "den",
        "der",
        "des",
        "die",
        "ein",
        "eine",
        "einem",
        "einen",
        "einer",
        "eines",
        "für",
        "im",
        "in",
        "mit",
        "nach",
        "oder",
        "und",
        "vom",
        "von",
        "vor",
        "zu",
        "zum",
        "zur",
    }
)

_TOKEN_RE = re.compile(r"[a-z0-9äöüß]+", re.I)


def normalize_label(text: str | None) -> str:
    raw = unicodedata.normalize("NFKC", str(text or "")).strip().lower()
    raw = raw.replace("ä", "ae").replace("ö", "oe").replace("ü", "ue").replace("ß", "ss")
    return re.sub(r"\s+", " ", raw).strip()


def label_tokens(label: str) -> list[str]:
    tokens = [t.lower() for t in _TOKEN_RE.findall(label or "")]
    return [t for t in tokens if len(t) >= 3 and t not in _STOPWORDS]


def label_in_text(label: str, blob: str) -> bool:
    normalized_label = normalize_label(label)
    if len(normalized_label) < 2:
        return False
    normalized_blob = normalize_label(blob)
    if normalized_label in normalized_blob:
        return True
    tokens = label_tokens(label)
    if not tokens:
        return False
    if len(tokens) >= 2:
        return all(token in normalized_blob for token in tokens)
    token = tokens[0]
    if len(token) < 4:
        return token in normalized_blob.split()
    return token in normalized_blob


def guess_method_id(label: str, *, when: str = "", example: str = "") -> str | None:
    combined = f"{label} {when} {example}".strip()
    if not combined:
        return None
    guessed = classify_method(combined)
    if guessed and guessed != "other":
        return guessed
    return None


def resolve_method_entry(item: dict) -> dict[str, str]:
    """Normalisiert eine Methoden-Zeile: label primär, id optional."""
    label = str(item.get("label") or "").strip()
    when = str(item.get("when") or "").strip()
    example = str(item.get("example") or "").strip()
    raw_id = str(item.get("id") or "").strip().lower()
    method_id = normalize_method_id(raw_id) if raw_id else None
    if not method_id:
        method_id = guess_method_id(label, when=when, example=example)
    if not label:
        if method_id and method_id in METHOD_LABELS:
            label = METHOD_LABELS[method_id]
        elif raw_id and raw_id not in {"other", ""}:
            label = raw_id
    if not label and not when and not example:
        return {}
    entry: dict[str, str] = {
        "label": label[:120] if label else (method_id or "Methode"),
        "when": when[:300],
        "example": example[:300],
    }
    if method_id:
        entry["id"] = method_id
    return entry


def material_labels_from_methods(methods: list) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for method in methods:
        if not isinstance(method, dict):
            continue
        label = str(method.get("label") or "").strip()
        if not label:
            method_id = normalize_method_id(method.get("id"))
            if method_id and method_id in METHOD_LABELS:
                label = METHOD_LABELS[method_id]
        if not label:
            continue
        key = normalize_label(label)
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(label)
    return out


def collect_content_blob(modules: list) -> str:
    parts: list[str] = []
    for mod in modules:
        if not isinstance(mod, dict):
            continue
        content = mod.get("content") if isinstance(mod.get("content"), dict) else {}
        for card in content.get("cards") or []:
            if not isinstance(card, dict):
                continue
            for key in ("question", "answer", "tip", "method_label"):
                parts.append(str(card.get(key) or ""))
            method_id = normalize_method_id(card.get("method_id") or card.get("expected_method"))
            if method_id and method_id in METHOD_LABELS:
                parts.append(METHOD_LABELS[method_id])
        knowledge = content.get("knowledge") or []
        if isinstance(knowledge, list):
            for item in knowledge:
                if isinstance(item, dict):
                    parts.append(str(item.get("title") or ""))
                    parts.append(str(item.get("text") or ""))
        for q in (mod.get("quiz") or {}).get("questions") or []:
            if not isinstance(q, dict):
                continue
            parts.append(str(q.get("q") or ""))
            parts.append(str(q.get("explanation") or ""))
            for opt in q.get("options") or []:
                parts.append(str(opt))
            method_id = normalize_method_id(q.get("method_id"))
            if method_id and method_id in METHOD_LABELS:
                parts.append(METHOD_LABELS[method_id])
    return " ".join(parts)


def count_label_coverage(labels: list[str], blob: str) -> int:
    return sum(1 for label in labels if label_in_text(label, blob))
