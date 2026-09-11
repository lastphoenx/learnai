"""Ableitung von Übungsaufgaben — Wissensabfrage statt generischer Schema-/Zeichenaufgaben."""

from __future__ import annotations

import re
from typing import Any

from app.core.basiswissen import derive_concept_quiz_questions
from app.core.focus_groups import normalize_focus_group
from app.core.label_diagram import (
    build_label_diagram_from_terms,
    is_label_format,
)

_PERSONAL_TERM = re.compile(
    r"gefallt|wünsche|wuerde ich|würde ich|deine|dein |meine|mein |gedanken|beobachtest|"
    r"erlebst|zukunft|mindmap.*schweiz heute",
    re.I,
)
_UNUSABLE_VISUAL = re.compile(
    r"bild der|abbildung|foto|altstadt.*beschrif|landmark|zeichne.*landschaft|nach deiner fantasie",
    re.I,
)


def _terms_from_key_terms(pedagogy: dict[str, Any]) -> list[str]:
    terms: list[str] = []
    seen: set[str] = set()
    for item in pedagogy.get("key_terms") or []:
        if not isinstance(item, dict):
            continue
        term = str(item.get("term") or "").strip()
        key = term.lower()
        if term and key not in seen and not _PERSONAL_TERM.search(term):
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
            if term and key not in seen and not _PERSONAL_TERM.search(term):
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
        if term and definition and not _PERSONAL_TERM.search(term):
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
            if term and _PERSONAL_TERM.search(term):
                continue
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
    local = _terms_from_basiswissen(basiswissen)
    if len(local) >= 3:
        return local
    return collect_terms(pedagogy=pedagogy, basiswissen=basiswissen)


def _prompt_fingerprint(prompt: str) -> str:
    return re.sub(r"\s+", " ", str(prompt or "").strip().lower())[:240]


def _should_skip_prompt(*, prompt: str, practice_state: dict[str, Any] | None) -> bool:
    if not practice_state:
        return False
    fp = _prompt_fingerprint(prompt)
    if not fp:
        return False
    seen = practice_state.setdefault("knowledge_prompts", set())
    if fp in seen:
        return True
    seen.add(fp)
    return False


def _choice_practice_item(
    *,
    prompt: str,
    options: list[str],
    answer_index: int,
    hint: str | None,
    source: str = "basiswissen",
) -> dict[str, Any]:
    return {
        "prompt": prompt[:500],
        "hint": (hint or "")[:300] or None,
        "answer_type": "choice",
        "options": [str(o).strip() for o in options if str(o).strip()],
        "answer": str(answer_index),
        "source": source,
    }


def _derive_knowledge_choice_items(
    *,
    basiswissen: dict[str, Any],
    pedagogy: dict[str, Any],
    category_label: str,
    practice_state: dict[str, Any] | None,
    max_count: int = 3,
) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    label = category_label[:120] or "Thema"

    for question in derive_concept_quiz_questions(basiswissen, max_count=max_count):
        prompt = str(question.get("q") or "").strip()
        options = [str(o).strip() for o in (question.get("options") or []) if str(o).strip()]
        if len(options) < 2:
            continue
        if _should_skip_prompt(prompt=prompt, practice_state=practice_state):
            continue
        try:
            answer_index = int(question.get("answer"))
        except (TypeError, ValueError):
            continue
        if answer_index < 0 or answer_index >= len(options):
            continue
        hint = str(question.get("explanation") or "").strip() or None
        items.append(
            _choice_practice_item(
                prompt=prompt,
                options=options,
                answer_index=answer_index,
                hint=hint,
                source="basiswissen",
            )
        )

    if len(items) >= max_count:
        return items[:max_count]

    term_hints = collect_term_hints(pedagogy=pedagogy, basiswissen=basiswissen)
    pool = _module_terms(pedagogy=pedagogy, basiswissen=basiswissen)
    for term in pool:
        if len(items) >= max_count:
            break
        hint = term_hints.get(term)
        if not hint or len(hint) < 8:
            continue
        prompt = f"Welcher Fachbegriff passt zu «{hint}»? ({label})"
        if _should_skip_prompt(prompt=prompt, practice_state=practice_state):
            continue
        distractors = [t for t in pool if t.lower() != term.lower()][:3]
        while len(distractors) < 3:
            distractors.append(f"Begriff {len(distractors) + 1}")
        options = [term] + distractors[:3]
        order = sorted(range(4), key=lambda i: (options[i].lower(), i))
        shuffled = [options[i] for i in order]
        answer_index = shuffled.index(term)
        items.append(
            _choice_practice_item(
                prompt=prompt,
                options=shuffled,
                answer_index=answer_index,
                hint=f"Denk an das Thema «{label}».",
                source="pedagogy",
            )
        )

    return items[:max_count]


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


def _label_practice_item(*, diagram: dict[str, Any], hint: str, source: str) -> dict[str, Any]:
    import json

    expected = {str(hs["id"]): hs["accept"][0] for hs in diagram.get("hotspots") or []}
    return {
        "prompt": str(diagram.get("instruction") or "Ordne die Fachbegriffe am Schema zu."),
        "hint": hint,
        "answer_type": "label_diagram",
        "answer": json.dumps(expected, ensure_ascii=False),
        "diagram": diagram,
        "source": source,
    }


def derive_practice_items(
    *,
    pedagogy: dict[str, Any] | None,
    basiswissen: dict[str, Any] | None,
    category_label: str = "",
    focus_group: str | None = None,
    practice_state: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Erzeugt prüfbare Wissensaufgaben — keine generischen Mindmap-/Zeichen-Platzhalter."""
    pedagogy = pedagogy if isinstance(pedagogy, dict) else {}
    basiswissen = basiswissen if isinstance(basiswissen, dict) else {}
    normalize_focus_group(focus_group or basiswissen.get("focus_group"))
    term_hints = collect_term_hints(pedagogy=pedagogy, basiswissen=basiswissen)
    items: list[dict[str, Any]] = []
    seen_prompts: set[str] = set()

    def add_item(item: dict[str, Any]) -> None:
        key = str(item.get("prompt") or "").strip().lower()
        if not key or key in seen_prompts:
            return
        if _UNUSABLE_VISUAL.search(key):
            return
        seen_prompts.add(key)
        items.append(item)

    title = category_label[:120] or "Thema"

    for item in _derive_knowledge_choice_items(
        basiswissen=basiswissen,
        pedagogy=pedagogy,
        category_label=title,
        practice_state=practice_state,
        max_count=3,
    ):
        add_item(item)

    if _visual_tasks_have_label_placements(pedagogy):
        for task in pedagogy.get("visual_tasks") or []:
            if not isinstance(task, dict):
                continue
            if not is_label_format(str(task.get("kind") or "")):
                continue
            instruction = str(task.get("instruction") or "").strip()
            if instruction and _UNUSABLE_VISUAL.search(instruction):
                continue
            placements = task.get("placements")
            if not isinstance(placements, list) or len(placements) < 3:
                continue
            task_terms = [str(t).strip() for t in (task.get("terms") or []) if str(t).strip()]
            use_terms = [t for t in (task_terms or _module_terms(pedagogy=pedagogy, basiswissen=basiswissen)) if t]
            diagram = build_label_diagram_from_terms(
                use_terms,
                title=f"{title} — Begriffe zuordnen",
                instruction=instruction or None,
                placements=placements,
                term_hints=term_hints,
                layout="radial",
            )
            if diagram:
                add_item(
                    _label_practice_item(
                        diagram=diagram,
                        hint="Lies den Hinweis — welcher Begriff passt?",
                        source="pedagogy",
                    )
                )

    return items[:3]
