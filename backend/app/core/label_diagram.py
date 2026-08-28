"""Diagramm-Beschriftung: Vorlagen, Ableitung aus Basiswissen, Bewertung."""

from __future__ import annotations

import json
import re
import unicodedata
from typing import Any

_CASTLE_HOTSPOTS: dict[str, dict[str, Any]] = {
    "bergfried": {"x": 0.74, "y": 0.10, "keywords": ["bergfried", "hauptturm", "keep"]},
    "wehrgang": {"x": 0.54, "y": 0.34, "keywords": ["wehrgang", "wergang", "zinnen", "mauerkamm"]},
    "pechnase": {"x": 0.58, "y": 0.40, "keywords": ["pechnase", "pechnasen", "machicolation"]},
    "ringmauer": {"x": 0.36, "y": 0.46, "keywords": ["ringmauer", "festungsmauer", "burgmauer"]},
    "palas": {"x": 0.64, "y": 0.48, "keywords": ["palas", "wohngebäude", "palace"]},
    "fallgatter": {"x": 0.47, "y": 0.66, "keywords": ["fallgatter", "gittertor", "portcullis", "tor"]},
    "eingang": {"x": 0.44, "y": 0.58, "keywords": ["eingang", "torweg", "brücke", "zugbrücke"]},
    "burggraben": {"x": 0.14, "y": 0.80, "keywords": ["burggraben", "wassergraben", "graben", "moat"]},
}

_DIAGRAM_KEYWORDS: dict[str, tuple[str, ...]] = {
    "castle": ("burg", "schloss", "mittelalter", "festung", "turm", "bergfried", "ritter"),
}


def _norm(text: str) -> str:
    raw = unicodedata.normalize("NFKC", str(text or "")).strip().lower()
    raw = raw.replace("ä", "ae").replace("ö", "oe").replace("ü", "ue").replace("ß", "ss")
    return re.sub(r"[^a-z0-9]+", "", raw)


def _concept_blob(concepts: list[dict[str, Any]]) -> str:
    parts: list[str] = []
    for concept in concepts:
        if not isinstance(concept, dict):
            continue
        parts.append(str(concept.get("label") or ""))
        parts.append(str(concept.get("pattern") or ""))
        parts.append(str(concept.get("hint") or ""))
        for item in concept.get("parts") or []:
            if isinstance(item, dict):
                parts.append(str(item.get("term") or ""))
                parts.append(str(item.get("role") or ""))
    return " ".join(parts).lower()


def detect_diagram_template(concepts: list[dict[str, Any]], *, category_label: str = "") -> str | None:
    blob = f"{category_label} {_concept_blob(concepts)}".lower()
    for template, keywords in _DIAGRAM_KEYWORDS.items():
        if any(keyword in blob for keyword in keywords):
            return template
    return None


def _match_hotspot(term: str, role: str, template: str) -> str | None:
    if template != "castle":
        return None
    hay = f"{term} {role}".lower()
    hay_norm = _norm(hay)
    best_id: str | None = None
    best_score = 0
    for hotspot_id, meta in _CASTLE_HOTSPOTS.items():
        for keyword in meta["keywords"]:
            kw_norm = _norm(keyword)
            if not kw_norm:
                continue
            if kw_norm in hay_norm or hay_norm in kw_norm:
                score = len(kw_norm)
                if score > best_score:
                    best_score = score
                    best_id = hotspot_id
    return best_id


def build_label_diagram(
    concepts: list[dict[str, Any]],
    *,
    template: str,
    title: str = "Fachbegriffe zuordnen",
) -> dict[str, Any] | None:
    if template != "castle":
        return None
    hotspots: list[dict[str, Any]] = []
    terms: list[str] = []
    used_ids: set[str] = set()
    for concept in concepts:
        if not isinstance(concept, dict):
            continue
        for part in concept.get("parts") or []:
            if not isinstance(part, dict):
                continue
            term = str(part.get("term") or "").strip()
            if not term:
                continue
            role = str(part.get("role") or "").strip()
            hotspot_id = _match_hotspot(term, role, template)
            if not hotspot_id or hotspot_id in used_ids:
                continue
            used_ids.add(hotspot_id)
            meta = _CASTLE_HOTSPOTS[hotspot_id]
            aliases = [term]
            for alias in part.get("aliases") or []:
                alias_text = str(alias).strip()
                if alias_text and alias_text not in aliases:
                    aliases.append(alias_text)
            hotspots.append(
                {
                    "id": hotspot_id,
                    "x": meta["x"],
                    "y": meta["y"],
                    "accept": aliases[:4],
                }
            )
            terms.append(term)
    if len(hotspots) < 3:
        return None
    return {
        "template": template,
        "title": title[:120],
        "instruction": "Tippe einen Begriff an, dann die passende Stelle auf dem Bild.",
        "hotspots": hotspots[:8],
        "terms": terms[:8],
    }


def grade_label_diagram_answer(expected: str, user_answer: str) -> bool:
    try:
        expected_map = json.loads(expected)
        user_map = json.loads(user_answer)
    except (json.JSONDecodeError, TypeError):
        return False
    if not isinstance(expected_map, dict) or not isinstance(user_map, dict):
        return False
    if set(expected_map.keys()) != set(user_map.keys()):
        return False
    for key, expected_term in expected_map.items():
        user_term = str(user_map.get(key) or "").strip()
        accepted = expected_term if isinstance(expected_term, list) else [expected_term]
        accepted_norm = {_norm(str(item)) for item in accepted if str(item).strip()}
        if _norm(user_term) not in accepted_norm:
            return False
    return True


def derive_label_practice_items(
    basiswissen: dict[str, Any],
    *,
    category_label: str = "",
) -> list[dict[str, Any]]:
    focus = str(basiswissen.get("focus_group") or "general").strip().lower()
    if focus not in {"mgu", "nature", "general"}:
        return []
    concepts = [c for c in (basiswissen.get("concepts") or []) if isinstance(c, dict)]
    template = detect_diagram_template(concepts, category_label=category_label)
    if not template:
        return []
    diagram = build_label_diagram(
        concepts,
        template=template,
        title=f"{category_label or 'Thema'} beschriften",
    )
    if not diagram:
        return []
    expected = {str(hs["id"]): hs["accept"][0] for hs in diagram["hotspots"]}
    return [
        {
            "prompt": str(diagram.get("instruction") or "Beschrifte das Bild mit den Fachbegriffen."),
            "hint": "Lies die Fachbegriffe im Wissens-Hub, wenn du unsicher bist.",
            "answer_type": "label_diagram",
            "answer": json.dumps(expected, ensure_ascii=False),
            "diagram": diagram,
            "source": "basiswissen",
        }
    ]


def derive_drawing_practice_item(
    basiswissen: dict[str, Any],
    *,
    category_label: str = "",
) -> dict[str, Any] | None:
    focus = str(basiswissen.get("focus_group") or "general").strip().lower()
    if focus not in {"mgu", "nature"}:
        return None
    concepts = [c for c in (basiswissen.get("concepts") or []) if isinstance(c, dict)]
    template = detect_diagram_template(concepts, category_label=category_label)
    terms: list[str] = []
    seen: set[str] = set()
    for concept in concepts:
        for part in concept.get("parts") or []:
            if not isinstance(part, dict):
                continue
            term = str(part.get("term") or "").strip()
            key = _norm(term)
            if term and key not in seen:
                seen.add(key)
                terms.append(term)
    if len(terms) < 3:
        return None
    if template != "castle":
        return None
    return {
        "prompt": (
            "Zeichne deine Burg in die Landschaft und beschrifte sie mit den Fachbegriffen "
            "(wie im Schulheft). Du kannst das Bild ausdrucken oder als PNG speichern."
        ),
        "hint": f"Begriffe zum Beschriften: {', '.join(terms[:8])}",
        "answer_type": "drawing",
        "answer": "complete",
        "drawing": {
            "background": "landscape",
            "terms": terms[:10],
            "title": category_label[:120] or "Zeichenaufgabe",
        },
        "source": "basiswissen",
    }
