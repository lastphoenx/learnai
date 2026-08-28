"""Ableitung von Übungsaufgaben aus Didaktik + Basiswissen — fachneutral."""

from __future__ import annotations

import json
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
        "hint": hint[:300],
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


def derive_practice_items(
    *,
    pedagogy: dict[str, Any] | None,
    basiswissen: dict[str, Any] | None,
    category_label: str = "",
    focus_group: str | None = None,
) -> list[dict[str, Any]]:
    pedagogy = pedagogy if isinstance(pedagogy, dict) else {}
    basiswissen = basiswissen if isinstance(basiswissen, dict) else {}
    group = normalize_focus_group(focus_group or basiswissen.get("focus_group"))
    terms = collect_terms(pedagogy=pedagogy, basiswissen=basiswissen)
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
            diagram = build_label_diagram_from_terms(
                use_terms,
                title=f"{title} beschriften",
                instruction=instruction or None,
                placements=placements,
            )
            if diagram:
                add_item(
                    _label_practice_item(
                        diagram=diagram,
                        hint="Nutze die Fachbegriffe im Wissens-Hub.",
                        source="pedagogy",
                    )
                )
        elif is_draw_format(kind):
            add_item(
                _drawing_practice_item(
                    prompt=instruction
                    or "Zeichne die Aufgabe und beschrifte sie mit den Fachbegriffen.",
                    terms=use_terms,
                    title=title,
                    hint=f"Begriffe: {', '.join(use_terms[:8])}" if use_terms else "",
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
            add_item(
                _drawing_practice_item(
                    prompt=instruction,
                    terms=terms,
                    title=title,
                    hint=f"Begriffe zum Beschriften: {', '.join(terms[:8])}" if terms else "",
                    source="pedagogy",
                )
            )
        elif is_label_format(fmt) and terms:
            diagram = build_label_diagram_from_terms(
                terms,
                title=f"{title} beschriften",
                instruction=instruction,
            )
            if diagram:
                add_item(
                    _label_practice_item(
                        diagram=diagram,
                        hint="Ordne jeden Begriff der passenden Stelle zu.",
                        source="pedagogy",
                    )
                )

    if not any(i.get("answer_type") == "label_diagram" for i in items):
        if terms and (_formats_imply_label(pedagogy) or is_nmg_focus(group)):
            diagram = build_label_diagram_from_terms(
                terms,
                title=f"{title} beschriften",
                instruction="Ordne die Fachbegriffe den passenden Stellen auf dem Schema zu.",
            )
            if diagram:
                add_item(
                    _label_practice_item(
                        diagram=diagram,
                        hint="Lies die Merksätze im Wissens-Hub.",
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
            add_item(
                _drawing_practice_item(
                    prompt=draw_prompt
                    or "Zeichne die Aufgabe wie im Heft und beschrifte sie mit den Fachbegriffen. "
                    "Du kannst das Bild ausdrucken oder als PNG speichern.",
                    terms=terms,
                    title=title,
                    hint=f"Begriffe: {', '.join(terms[:8])}" if terms else "",
                    source="pedagogy",
                )
            )

    return items[:4]
