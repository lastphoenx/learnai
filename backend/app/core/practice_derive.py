"""Ableitung von Übungsaufgaben aus Didaktik + Basiswissen — fachneutral."""

from __future__ import annotations

import json
import re
from typing import Any

from app.core.focus_groups import is_nmg_focus, normalize_focus_group
from app.core.label_diagram import (
    build_label_diagram_from_terms,
    is_draw_format,
    is_label_format,
)


def _terms_from_key_terms(pedagogy: dict[str, Any]) -> list[str]:
    terms: list[str] = []
    seen: set[str] = set()
    for item in pedagogy.get("key_terms") or []:
        if not isinstance(item, dict):
            continue
        term = str(item.get("term") or "").strip()
        key = term.lower()
        if term and key not in seen:
            seen.add(key)
            terms.append(term)
    return terms


def _terms_from_basiswissen(basiswissen: dict[str, Any]) -> list[str]:
    terms: list[str] = []
    seen: set[str] = set()
    for concept in basiswissen.get("concepts") or []:
        if not isinstance(concept, dict):
            continue
        for part in concept.get("parts") or []:
            if not isinstance(part, dict):
                continue
            term = str(part.get("term") or "").strip()
            key = term.lower()
            if term and key not in seen:
                seen.add(key)
                terms.append(term)
    return terms


def collect_terms(*, pedagogy: dict[str, Any] | None, basiswissen: dict[str, Any] | None) -> list[str]:
    pedagogy = pedagogy if isinstance(pedagogy, dict) else {}
    basiswissen = basiswissen if isinstance(basiswissen, dict) else {}
    merged: list[str] = []
    seen: set[str] = set()
    for term in _terms_from_key_terms(pedagogy) + _terms_from_basiswissen(basiswissen):
        key = term.lower()
        if key not in seen:
            seen.add(key)
            merged.append(term)
    return merged


def collect_term_hints(
    *,
    pedagogy: dict[str, Any] | None,
    basiswissen: dict[str, Any] | None,
) -> dict[str, str]:
    hints: dict[str, str] = {}
    pedagogy = pedagogy if isinstance(pedagogy, dict) else {}
    basiswissen = basiswissen if isinstance(basiswissen, dict) else {}

    for item in pedagogy.get("key_terms") or []:
        if not isinstance(item, dict):
            continue
        term = str(item.get("term") or "").strip()
        definition = str(item.get("definition") or item.get("hint") or "").strip()
        if term and definition:
            hints[term] = definition[:160]

    for concept in basiswissen.get("concepts") or []:
        if not isinstance(concept, dict):
            continue
        concept_hint = str(concept.get("hint") or concept.get("label") or "").strip()
        for part in concept.get("parts") or []:
            if not isinstance(part, dict):
                continue
            term = str(part.get("term") or "").strip()
            part_hint = str(part.get("hint") or part.get("role") or "").strip()
            if term and part_hint:
                hints[term] = part_hint[:160]
            elif term and concept_hint:
                hints[term] = concept_hint[:160]
    return hints


def _module_terms(
    *,
    pedagogy: dict[str, Any],
    basiswissen: dict[str, Any],
) -> list[str]:
    """Modul-spezifische Begriffe bevorzugen — nicht jedes Mal die globale PDF-Liste."""
    local = _terms_from_basiswissen(basiswissen)
    if len(local) >= 3:
        return local
    return collect_terms(pedagogy=pedagogy, basiswissen=basiswissen)


def _label_fingerprint(terms: list[str]) -> str:
    return "|".join(sorted(t.lower() for t in terms))


def _draw_fingerprint(prompt: str) -> str:
    return re.sub(r"\s+", " ", str(prompt or "").strip().lower())[:240]


def _pick_layout(*, terms: list[str], term_hints: dict[str, str]) -> str:
    joined = " ".join(term_hints.get(t, t) for t in terms).lower()
    if re.search(r"\d{3,4}\s*[-–]\s*\d{3,4}|n\.?\s*chr|jahrhundert|epoche|zeit", joined):
        return "timeline"
    if len(terms) >= 5 and any(k in joined for k in ("pyramide", "hierarch", "stufe", "ebene")):
        return "pyramid"
    return "radial"


def _label_practice_item(
    *,
    diagram: dict[str, Any],
    hint: str,
    source: str,
) -> dict[str, Any]:
    expected = {str(hs["id"]): hs["accept"][0] for hs in diagram.get("hotspots") or []}
    return {
        "prompt": str(diagram.get("instruction") or "Beschrifte das Schema mit den Fachbegriffen."),
        "hint": hint,
        "answer_type": "label_diagram",
        "answer": json.dumps(expected, ensure_ascii=False),
        "diagram": diagram,
        "source": source,
    }


def _drawing_practice_item(
    *,
    prompt: str,
    terms: list[str],
    title: str,
    hint: str,
    source: str,
) -> dict[str, Any]:
    return {
        "prompt": prompt[:500],
        "hint": hint[:300] if hint else None,
        "answer_type": "drawing",
        "answer": "complete",
        "drawing": {
            "background": "landscape",
            "terms": terms[:12],
            "title": title[:120],
        },
        "source": source,
    }


def _formats_imply_label(pedagogy: dict[str, Any]) -> bool:
    for pattern in pedagogy.get("exercise_formats") or []:
        if is_label_format(str(pattern)):
            return True
    for assignment in pedagogy.get("assignments") or []:
        if isinstance(assignment, dict) and is_label_format(str(assignment.get("format") or "")):
            return True
    return False


def _formats_imply_draw(pedagogy: dict[str, Any]) -> bool:
    for pattern in pedagogy.get("exercise_formats") or []:
        if is_draw_format(str(pattern)):
            return True
    for assignment in pedagogy.get("assignments") or []:
        if isinstance(assignment, dict) and is_draw_format(str(assignment.get("format") or "")):
            return True
    return False


def _visual_tasks_have_label_placements(pedagogy: dict[str, Any]) -> bool:
    for task in pedagogy.get("visual_tasks") or []:
        if not isinstance(task, dict):
            continue
        if not is_label_format(str(task.get("kind") or "")):
            continue
        placements = task.get("placements")
        if isinstance(placements, list) and len(placements) >= 3:
            return True
    return False


def _allow_generic_label_diagram(*, focus_group: str, pedagogy: dict[str, Any]) -> bool:
    """Deutsch ohne echte Bild-Placements: kein generisches Rad (didaktisch wertlos)."""
    group = normalize_focus_group(focus_group)
    if group != "german":
        return True
    return _visual_tasks_have_label_placements(pedagogy)


def _should_skip_label(*, terms: list[str], practice_state: dict[str, Any] | None) -> bool:
    if not practice_state:
        return False
    fp = _label_fingerprint(terms)
    seen = practice_state.setdefault("label_fingerprints", set())
    if fp in seen:
        return True
    seen.add(fp)
    return False


def _should_skip_draw(*, prompt: str, practice_state: dict[str, Any] | None) -> bool:
    if not practice_state:
        return False
    fp = _draw_fingerprint(prompt)
    if not fp:
        return False
    seen = practice_state.setdefault("draw_fingerprints", set())
    if fp in seen:
        return True
    seen.add(fp)
    return False


def _meaningful_draw_hint(*, prompt: str, terms: list[str], title: str) -> str:
    if re.search(r"burg|schloss|festung", f"{prompt} {title}".lower()):
        return "Skizziere Bergfried, Mauern und Tor — beschrifte die Teile, die du kennst."
    if terms and len(terms) >= 3:
        return "Zeichne die Situation aus dem Arbeitsblatt und beschrifte die wichtigsten Teile."
    return ""


def derive_practice_items(
    *,
    pedagogy: dict[str, Any] | None,
    basiswissen: dict[str, Any] | None,
    category_label: str = "",
    focus_group: str | None = None,
    practice_state: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    pedagogy = pedagogy if isinstance(pedagogy, dict) else {}
    basiswissen = basiswissen if isinstance(basiswissen, dict) else {}
    group = normalize_focus_group(focus_group or basiswissen.get("focus_group"))
    terms = _module_terms(pedagogy=pedagogy, basiswissen=basiswissen)
    term_hints = collect_term_hints(pedagogy=pedagogy, basiswissen=basiswissen)
    items: list[dict[str, Any]] = []
    seen_prompts: set[str] = set()

    def add_item(item: dict[str, Any]) -> None:
        key = str(item.get("prompt") or "").strip().lower()
        if not key or key in seen_prompts:
            return
        seen_prompts.add(key)
        items.append(item)

    title = category_label[:120] or "Thema"

    for task in pedagogy.get("visual_tasks") or []:
        if not isinstance(task, dict):
            continue
        kind = str(task.get("kind") or "").strip().lower()
        instruction = str(task.get("instruction") or "").strip()
        task_terms = [str(t).strip() for t in (task.get("terms") or []) if str(t).strip()]
        use_terms = task_terms or terms
        placements = task.get("placements") if isinstance(task.get("placements"), list) else None
        if is_label_format(kind) and use_terms:
            if _should_skip_label(terms=use_terms, practice_state=practice_state):
                continue
            if not _allow_generic_label_diagram(focus_group=group, pedagogy=pedagogy) and not placements:
                continue
            diagram = build_label_diagram_from_terms(
                use_terms,
                title=f"{title} — Begriffe zuordnen",
                instruction=instruction or None,
                placements=placements,
                term_hints=term_hints,
                layout=_pick_layout(terms=use_terms, term_hints=term_hints),
            )
            if diagram:
                add_item(
                    _label_practice_item(
                        diagram=diagram,
                        hint="Fahre über die Fragezeichen — dort steht, was an dieser Stelle gemeint ist.",
                        source="pedagogy",
                    )
                )
        elif is_draw_format(kind):
            draw_prompt = instruction or "Zeichne die Aufgabe und beschrifte sie mit den Fachbegriffen."
            if _should_skip_draw(prompt=draw_prompt, practice_state=practice_state):
                continue
            add_item(
                _drawing_practice_item(
                    prompt=draw_prompt,
                    terms=use_terms,
                    title=title,
                    hint=_meaningful_draw_hint(prompt=draw_prompt, terms=use_terms, title=title),
                    source="pedagogy",
                )
            )

    for assignment in pedagogy.get("assignments") or []:
        if not isinstance(assignment, dict):
            continue
        fmt = str(assignment.get("format") or "").strip()
        instruction = str(assignment.get("instruction") or "").strip()
        if not instruction:
            continue
        if is_draw_format(fmt):
            if _should_skip_draw(prompt=instruction, practice_state=practice_state):
                continue
            add_item(
                _drawing_practice_item(
                    prompt=instruction,
                    terms=terms,
                    title=title,
                    hint=_meaningful_draw_hint(prompt=instruction, terms=terms, title=title),
                    source="pedagogy",
                )
            )
        elif is_label_format(fmt) and terms:
            if _should_skip_label(terms=terms, practice_state=practice_state):
                continue
            if not _allow_generic_label_diagram(focus_group=group, pedagogy=pedagogy):
                continue
            diagram = build_label_diagram_from_terms(
                terms,
                title=f"{title} — Begriffe zuordnen",
                instruction=instruction,
                term_hints=term_hints,
                layout=_pick_layout(terms=terms, term_hints=term_hints),
            )
            if diagram:
                add_item(
                    _label_practice_item(
                        diagram=diagram,
                        hint="Fahre über die Fragezeichen — dort steht, was an dieser Stelle gemeint ist.",
                        source="pedagogy",
                    )
                )

    if not any(i.get("answer_type") == "label_diagram" for i in items):
        if terms and (_formats_imply_label(pedagogy) or is_nmg_focus(group)):
            if _should_skip_label(terms=terms, practice_state=practice_state):
                pass
            elif _allow_generic_label_diagram(focus_group=group, pedagogy=pedagogy):
                diagram = build_label_diagram_from_terms(
                    terms,
                    title=f"{title} — Begriffe zuordnen",
                    instruction="Ordne die Fachbegriffe anhand der Hinweise auf dem Schema zu.",
                    term_hints=term_hints,
                    layout=_pick_layout(terms=terms, term_hints=term_hints),
                )
                if diagram:
                    add_item(
                        _label_practice_item(
                            diagram=diagram,
                            hint="Fahre über die Fragezeichen — dort steht, was an dieser Stelle gemeint ist.",
                            source="basiswissen",
                        )
                    )

    if not any(i.get("answer_type") == "drawing" for i in items):
        if _formats_imply_draw(pedagogy):
            draw_prompt = ""
            for assignment in pedagogy.get("assignments") or []:
                if isinstance(assignment, dict) and is_draw_format(str(assignment.get("format") or "")):
                    draw_prompt = str(assignment.get("instruction") or "").strip()
                    break
            draw_prompt = (
                draw_prompt
                or "Zeichne die Aufgabe wie im Heft und beschrifte sie mit den Fachbegriffen. "
                "Du kannst das Bild ausdrucken oder als PNG speichern."
            )
            if not _should_skip_draw(prompt=draw_prompt, practice_state=practice_state):
                add_item(
                    _drawing_practice_item(
                        prompt=draw_prompt,
                        terms=terms,
                        title=title,
                        hint=_meaningful_draw_hint(prompt=draw_prompt, terms=terms, title=title),
                        source="pedagogy",
                    )
                )

    return items[:2]
