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

# Wörtliche Schema-/Prompt-Texte, die die Vision-KI manchmal als Inhalt zurückgibt.
_SCHEMA_PLACEHOLDERS = frozenset(
    {
        "wann diese methode sinnvoll ist",
        "kurzer satz wann passt diese strategie aus dem material",
        "kurzes beispiel aus dem bild",
        "kurzes beispiel mit zahlen text aus dem bild",
        "freier kurzname fur erkannten aufgabentyp",
        "freier kurzname fuer erkannten aufgabentyp",
        "kurzer name des aufgabentyps aus dem heft",
        "didaktische hinweise aus dem material",
        "konkreter didaktischer hinweis aus dem material",
        "bezeichnung exakt wie im heft",
        "bezeichnung wie im heft",
        "optional nur wenn passend",
        "optional bezeichnung aus dem heft",
        "2 6 saetze thema seiteninhalt lernziele",
        "aufgabe",
        "aufgabentext",
        "schritt 1",
        "schritt 2",
    }
)

# Anweisungs-Präfixe in Schema-Beschreibungen (nicht als echte Feldwerte).
_SCHEMA_PREFIXES = (
    "kurzer satz ",
    "kurzes beispiel ",
    "kurzer name des aufgabentyps",
    "konkreter didaktischer hinweis",
    "2 6 saetze ",
    "bezeichnung exakt wie",
    "bezeichnung wie im heft",
    "optional nur wenn",
    "optional bezeichnung",
)


def normalize_label(text: str | None) -> str:
    raw = unicodedata.normalize("NFKC", str(text or "")).strip().lower()
    raw = raw.replace("ä", "ae").replace("ö", "oe").replace("ü", "ue").replace("ß", "ss")
    raw = re.sub(r"[^\w\s]", " ", raw)
    return re.sub(r"\s+", " ", raw).strip()


def is_schema_placeholder(text: str | None) -> bool:
    """True, wenn der Wert nur die Schema-Beschreibung aus dem Vision-Prompt echo't."""
    normalized = normalize_label(text)
    if not normalized:
        return False
    if normalized in _SCHEMA_PLACEHOLDERS:
        return True
    if any(normalized.startswith(prefix) for prefix in _SCHEMA_PREFIXES):
        return True
    for placeholder in _SCHEMA_PLACEHOLDERS:
        if len(placeholder) >= 12 and placeholder in normalized and len(normalized) <= len(placeholder) + 8:
            return True
    return False


def sanitize_pedagogy_field(text: str | None) -> str:
    cleaned = str(text or "").strip()
    if is_schema_placeholder(cleaned):
        return ""
    return cleaned


def is_competency_heading(text: str | None) -> bool:
    """Lernziel-Überschriften («Du kannst…») sind keine Lösungswege."""
    normalized = normalize_label(text)
    if not normalized:
        return False
    return bool(
        re.search(r"(?:^|\s)(du kannst|du kennst|du weisst|du weiszt)\b", normalized)
    )


def is_competency_phrasing(text: str | None) -> bool:
    """Lernziele ohne «Du kannst» («… lösen», «so einsetzen, dass…»)."""
    if is_competency_heading(text):
        return True
    normalized = normalize_label(text)
    if not normalized:
        return False
    if re.search(r"\bzu losen\b", normalized):
        return True
    if re.search(r"\bso einsetzen\b", normalized):
        return True
    if len(normalized) >= 40 and re.search(r"(losen|einsetzen)$", normalized):
        return True
    return False


def method_fields_are_redundant(label: str | None, when: str | None) -> bool:
    """True, wenn label und when dieselbe Lernziel-Zeile sind (ggf. mit «bei …»)."""
    a = normalize_label(label)
    b = normalize_label(when)
    if not a or not b:
        return False
    a_core = re.sub(r"^(bei|wenn|zum|zur)\s+", "", a).strip()
    b_core = re.sub(r"^(bei|wenn|zum|zur)\s+", "", b).strip()
    if not a_core or not b_core:
        return False
    if a_core == b_core:
        return True
    shorter, longer = (a_core, b_core) if len(a_core) <= len(b_core) else (b_core, a_core)
    if len(shorter) >= 24 and shorter in longer:
        return True
    ta = {t for t in a_core.split() if t not in _STOPWORDS and len(t) >= 3}
    tb = {t for t in b_core.split() if t not in _STOPWORDS and len(t) >= 3}
    if len(ta) >= 6 and len(tb) >= 6:
        overlap = len(ta & tb) / len(ta | tb)
        if overlap >= 0.85:
            return True
    return False


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
    label = sanitize_pedagogy_field(str(item.get("label") or "").strip())
    when = sanitize_pedagogy_field(str(item.get("when") or "").strip())
    example = sanitize_pedagogy_field(str(item.get("example") or "").strip())
    if is_competency_heading(example):
        example = ""
    if (
        is_competency_phrasing(label)
        or is_competency_heading(when)
        or method_fields_are_redundant(label, when)
    ):
        return {}
    if is_competency_phrasing(when) and len(normalize_label(when)) >= 40:
        return {}
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
