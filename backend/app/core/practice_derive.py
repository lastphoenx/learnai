"""Ableitung von Übungsaufgaben — Wissensabfrage statt generischer Schema-/Zeichenaufgaben."""

from __future__ import annotations

import re
from typing import Any

from app.core.focus_groups import normalize_focus_group
from app.core.label_diagram import (
    build_label_diagram_from_terms,
    is_label_format,
)
from app.core.timeline_diagram import build_timeline_diagram_from_pedagogy, summarize_timeline
from app.core.visual_task_filters import (
    has_degenerate_placements,
    is_unusable_visual_instruction,
)

_PERSONAL_TERM = re.compile(
    r"gefallt|wünsche|wuerde ich|würde ich|deine|dein |meine|mein |gedanken|beobachtest|"
    r"erlebst|zukunft|mindmap.*schweiz heute",
    re.I,
)
_UNUSABLE_VISUAL = re.compile(
    r"bild der|abbildung|foto|altstadt.*beschrif|landmark|"
    r"zeichne.*landschaft|nach deiner fantasie|"
    r"symbol.*gegenwart|zeichne.*symbol|typisch.*21|"
    r"leeres feld|deiner meinung|gegenstand.*typisch",
    re.I,
)
_WEAK_ROLES = frozenset({"begriff", "part", "whole", "term", "definition", "concept", "element", "item"})
_PLACEHOLDER_OPTION = re.compile(r"^(Antwort|Begriff)\s+\d+$", re.I)
_DEFINITION_LIKE = re.compile(r"^(der|die|das|ein|eine|historische|politische)\s+", re.I)


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
            part_hint = str(part.get("hint") or "").strip()
            if term and _PERSONAL_TERM.search(term):
                continue
            if term and part_hint and part_hint.lower() != str(part.get("role") or "").strip().lower():
                hints[term] = part_hint[:160]
            elif term and concept_hint and concept_hint.lower() != term.lower():
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
    if practice_state is None:
        return False
    fp = _prompt_fingerprint(prompt)
    if not fp:
        return False
    seen = practice_state.setdefault("knowledge_prompts", set())
    if fp in seen:
        return True
    seen.add(fp)
    return False


def _is_sentence_like(text: str) -> bool:
    t = text.strip()
    return len(t) > 64 or t.count(" ") >= 7 or t.endswith((".", "?", "!"))


def _short_topic(text: str) -> str:
    words = text.split()
    if len(words) <= 5 and len(text) <= 48:
        return text
    return " ".join(words[:5])


def _concept_term_pool(concepts: list[dict[str, Any]]) -> list[str]:
    terms: list[str] = []
    seen: set[str] = set()
    for concept in concepts:
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


def _normalize_option_set(options: list[str]) -> tuple[str, ...]:
    return tuple(sorted(str(o).strip().lower() for o in options if str(o).strip()))


def _option_set_already_used(*, options: list[str], practice_state: dict[str, Any] | None) -> bool:
    if practice_state is None:
        return False
    normalized = _normalize_option_set(options)
    if len(normalized) < 2:
        return False
    seen = practice_state.get("knowledge_option_sets")
    return isinstance(seen, set) and normalized in seen


def _remember_option_set(*, options: list[str], practice_state: dict[str, Any] | None) -> None:
    if practice_state is None:
        return
    normalized = _normalize_option_set(options)
    if len(normalized) < 2:
        return
    practice_state.setdefault("knowledge_option_sets", set()).add(normalized)


def _is_definition_like_term(text: str) -> bool:
    cleaned = re.sub(r"\s+", " ", str(text or "").strip())
    if len(cleaned) < 40:
        return False
    if cleaned.count(" ") < 5:
        return False
    return bool(_DEFINITION_LIKE.search(cleaned) or cleaned.endswith("."))


def _distractor_candidates(*, pool: list[str], correct: str, siblings: list[str]) -> list[str]:
    candidates = [t for t in siblings + pool if t.lower() != correct.lower()]
    deduped: list[str] = []
    seen: set[str] = {correct.lower()}
    for term in candidates:
        key = term.lower()
        if key in seen or _is_definition_like_term(term):
            continue
        seen.add(key)
        deduped.append(term)
    return deduped


def _should_skip_option_set(*, options: list[str], practice_state: dict[str, Any] | None) -> bool:
    if _option_set_already_used(options=options, practice_state=practice_state):
        return True
    _remember_option_set(options=options, practice_state=practice_state)
    return False


def _pick_distractors(
    *,
    pool: list[str],
    correct: str,
    siblings: list[str],
    count: int = 3,
    seed: str = "",
) -> list[str]:
    deduped = _distractor_candidates(pool=pool, correct=correct, siblings=siblings)
    if not deduped:
        return []
    offset = sum(ord(ch) for ch in seed) % len(deduped)
    rotated = deduped[offset:] + deduped[:offset]
    return rotated[:count]


def _pick_unique_mc_options(
    *,
    pool: list[str],
    correct: str,
    siblings: list[str],
    practice_state: dict[str, Any] | None,
    seed: str = "",
) -> tuple[list[str], int] | None:
    """MC-Optionen wählen und dabei bereits vergebene 4er-Sets vermeiden."""
    deduped = _distractor_candidates(pool=pool, correct=correct, siblings=siblings)
    if len(deduped) < 2:
        return None
    base = sum(ord(ch) for ch in seed) % len(deduped)
    for attempt in range(len(deduped)):
        offset = (base + attempt) % len(deduped)
        rotated = deduped[offset:] + deduped[:offset]
        shuffled = _shuffle_mc_options(correct, rotated[:3])
        if not shuffled:
            continue
        options, answer_idx = shuffled
        if _option_set_already_used(options=options, practice_state=practice_state):
            continue
        _remember_option_set(options=options, practice_state=practice_state)
        return options, answer_idx
    return None


def _shuffle_mc_options(correct: str, distractors: list[str]) -> tuple[list[str], int] | None:
    if len(distractors) < 2:
        return None
    options = [correct] + distractors[: min(3, len(distractors))]
    if len({o.lower() for o in options}) < len(options):
        return None
    order = sorted(range(len(options)), key=lambda i: (options[i].lower(), i))
    shuffled = [options[i] for i in order]
    return shuffled, shuffled.index(correct)


def _scrub_clue(text: str, term: str) -> str | None:
    raw = re.sub(r"\s+", " ", text.strip())
    if len(raw) < 16:
        return None
    if term.lower() not in raw.lower():
        return raw[:220]
    clue = re.sub(re.escape(term), "…", raw, flags=re.I)
    clue = re.sub(r"\s+", " ", clue).strip(" .—–-")
    if len(clue) < 14 or clue in {"…", "….", "… …"}:
        return None
    return clue[:220]


def _definition_clue(concept: dict[str, Any], part: dict[str, Any]) -> str | None:
    term = str(part.get("term") or "").strip()
    for raw in (
        str(part.get("hint") or "").strip(),
        str(concept.get("hint") or "").strip(),
        str(concept.get("example") or "").strip(),
    ):
        if not raw or raw.lower() == term.lower():
            continue
        clue = _scrub_clue(raw, term)
        if clue:
            return clue
    return None


def _is_weak_practice_prompt(prompt: str, correct: str, options: list[str]) -> bool:
    if len(prompt.strip()) < 12:
        return True
    if any(_PLACEHOLDER_OPTION.match(str(o).strip()) for o in options):
        return True
    if len({str(o).strip().lower() for o in options if str(o).strip()}) < len(options):
        return True
    if _is_definition_like_term(correct):
        return True
    if any(_is_definition_like_term(str(o)) for o in options if str(o).strip().lower() != correct.lower()):
        return True
    lower = prompt.lower()
    if f"«{correct}»" in prompt and "was bezeichnet" in lower:
        return True
    if lower.startswith("was bedeutet") and f"«{correct}»" in prompt:
        if "gemeint" not in lower and "passt" not in lower:
            return True
    return False


def derive_practice_choice_questions(
    basiswissen: dict[str, Any],
    *,
    category_label: str = "",
    max_count: int = 3,
) -> list[dict[str, Any]]:
    """Prüfbare MC-Aufgaben — Definition/Lücke statt «Was bezeichnet X bei X?»."""
    from app.core.basiswissen import _pattern_lists_multiple_parts
    from app.core.basiswissen_profiles import ROLE_LABELS_DE

    concepts = [c for c in (basiswissen.get("concepts") or []) if isinstance(c, dict)]
    if not concepts:
        return []
    pool = _concept_term_pool(concepts)
    topic = _short_topic(category_label or "Thema")
    questions: list[dict[str, Any]] = []

    for template in basiswissen.get("cloze_templates") or []:
        if len(questions) >= max_count:
            break
        if not isinstance(template, dict):
            continue
        answers = template.get("answers") or []
        sentence = str(template.get("sentence") or "").strip()
        if not answers or not sentence or "___" not in sentence:
            continue
        correct = str(answers[0]).strip()
        if not correct:
            continue
        distractors = _pick_distractors(pool=pool, correct=correct, siblings=[], seed=correct)
        shuffled = _shuffle_mc_options(correct, distractors)
        if not shuffled:
            continue
        options, answer_idx = shuffled
        prompt = f"Welcher Begriff fehlt?\n{sentence}"
        if _is_weak_practice_prompt(prompt, correct, options):
            continue
        questions.append(
            {
                "q": prompt[:400],
                "options": options,
                "answer": answer_idx,
                "concept_id": str(template.get("concept_id") or "")[:64],
                "target_term": correct[:80],
                "style": "cloze",
            }
        )

    for concept in concepts:
        if len(questions) >= max_count:
            break
        concept_topic = _short_topic(str(concept.get("label") or topic))
        if _is_sentence_like(concept_topic):
            concept_topic = topic
        siblings = _concept_term_pool([concept])
        for part in concept.get("parts") or []:
            if len(questions) >= max_count:
                break
            if not isinstance(part, dict):
                continue
            correct = str(part.get("term") or "").strip()
            clue = _definition_clue(concept, part)
            if not correct or not clue:
                continue
            distractors = _pick_distractors(
                pool=pool,
                correct=correct,
                siblings=[t for t in siblings if t.lower() != correct.lower()],
                seed=f"{concept.get('id')}:{correct}",
            )
            shuffled = _shuffle_mc_options(correct, distractors)
            if not shuffled:
                continue
            options, answer_idx = shuffled
            prompt = f"Welcher Fachbegriff passt? «{clue}» (Thema: {concept_topic})"
            if _is_weak_practice_prompt(prompt, correct, options):
                continue
            questions.append(
                {
                    "q": prompt[:400],
                    "options": options,
                    "answer": answer_idx,
                    "concept_id": str(concept.get("id") or "")[:64],
                    "target_term": correct[:80],
                    "style": "definition",
                    "clue": clue[:220],
                }
            )

    for concept in concepts:
        if len(questions) >= max_count:
            break
        pattern = str(concept.get("pattern") or "").strip()
        parts = [p for p in (concept.get("parts") or []) if isinstance(p, dict)]
        if not parts or not (_pattern_lists_multiple_parts(pattern, parts) or len(parts) > 1):
            continue
        label = _short_topic(str(concept.get("label") or topic))
        if _is_sentence_like(label):
            label = topic
        siblings = _concept_term_pool([concept])
        for part in parts:
            if len(questions) >= max_count:
                break
            role = str(part.get("role") or "").strip().lower()
            if role in _WEAK_ROLES:
                continue
            role_label = ROLE_LABELS_DE.get(role, "")
            if not role_label or role_label.lower() in _WEAK_ROLES:
                continue
            correct = str(part.get("term") or "").strip()
            if not correct:
                continue
            distractors = _pick_distractors(
                pool=pool,
                correct=correct,
                siblings=[t for t in siblings if t.lower() != correct.lower()],
                seed=f"{concept.get('id')}:{correct}",
            )
            shuffled = _shuffle_mc_options(correct, distractors)
            if not shuffled:
                continue
            options, answer_idx = shuffled
            if pattern:
                prompt = f"Bei «{label}» ({pattern}): Welcher Begriff ist der {role_label}?"
            else:
                prompt = f"Bei «{label}»: Welcher Begriff ist der {role_label}?"
            if _is_weak_practice_prompt(prompt, correct, options):
                continue
            questions.append(
                {
                    "q": prompt[:400],
                    "options": options,
                    "answer": answer_idx,
                    "concept_id": str(concept.get("id") or "")[:64],
                    "target_term": correct[:80],
                    "style": "relation",
                }
            )

    return questions[:max_count]


def _practice_hint_from_question(
    question: dict[str, Any],
    basiswissen: dict[str, Any],
) -> str | None:
    clue = str(question.get("clue") or "").strip()
    if len(clue) >= 12:
        return None
    concept_id = str(question.get("concept_id") or "").strip()
    for concept in basiswissen.get("concepts") or []:
        if not isinstance(concept, dict):
            continue
        if concept_id and str(concept.get("id") or "").strip() != concept_id:
            continue
        hint = str(concept.get("hint") or "").strip()
        if len(hint) >= 12:
            return hint[:300]
        example = str(concept.get("example") or "").strip()
        if len(example) >= 12:
            return example[:300]
        pattern = str(concept.get("pattern") or "").strip()
        if len(pattern) >= 12:
            return f"Denk an: {pattern[:240]}"
    return "Nutze den Wissens-Hub im Modul."


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
    pool = _module_terms(pedagogy=pedagogy, basiswissen=basiswissen)

    for question in derive_practice_choice_questions(basiswissen, category_label=label, max_count=max_count):
        prompt = str(question.get("q") or "").strip()
        options = [str(o).strip() for o in (question.get("options") or []) if str(o).strip()]
        if len(options) < 2:
            continue
        if _should_skip_prompt(prompt=prompt, practice_state=practice_state):
            continue
        correct_term = str(question.get("target_term") or "").strip()
        try:
            answer_index = int(question.get("answer"))
        except (TypeError, ValueError):
            answer_index = -1
        if answer_index < 0 or answer_index >= len(options):
            continue
        if not correct_term:
            correct_term = options[answer_index]
        if _option_set_already_used(options=options, practice_state=practice_state):
            alt = _pick_unique_mc_options(
                pool=pool,
                correct=correct_term,
                siblings=_concept_term_pool([c for c in (basiswissen.get("concepts") or []) if isinstance(c, dict)]),
                practice_state=practice_state,
                seed=f"{question.get('concept_id')}:{correct_term}",
            )
            if not alt:
                continue
            options, answer_index = alt
        else:
            _remember_option_set(options=options, practice_state=practice_state)
        hint = _practice_hint_from_question(question, basiswissen)
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
    for term in pool:
        if len(items) >= max_count:
            break
        hint = term_hints.get(term)
        if not hint or len(hint) < 12:
            continue
        clue = _scrub_clue(hint, term)
        if not clue:
            continue
        prompt = f"Welcher Fachbegriff passt? «{clue}» (Thema: {_short_topic(label)})"
        if _should_skip_prompt(prompt=prompt, practice_state=practice_state):
            continue
        picked = _pick_unique_mc_options(
            pool=pool,
            correct=term,
            siblings=[],
            practice_state=practice_state,
            seed=term,
        )
        if not picked:
            continue
        options, answer_index = picked
        if _is_weak_practice_prompt(prompt, term, options):
            continue
        items.append(
            _choice_practice_item(
                prompt=prompt,
                options=options,
                answer_index=answer_index,
                hint=None,
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
    has_timeline = summarize_timeline(pedagogy) is not None
    choice_cap = 2 if has_timeline else 3

    for item in _derive_knowledge_choice_items(
        basiswissen=basiswissen,
        pedagogy=pedagogy,
        category_label=title,
        practice_state=practice_state,
        max_count=choice_cap,
    ):
        add_item(item)

    timeline_diagram = build_timeline_diagram_from_pedagogy(
        pedagogy,
        title=f"{title} — Zeitstrahl",
        term_hints=term_hints,
    )
    if timeline_diagram:
        if practice_state is not None and practice_state.get("unit_timeline_diagram"):
            timeline_diagram = None
        else:
            if practice_state is not None:
                practice_state["unit_timeline_diagram"] = True
            timeline_item = _label_practice_item(
                diagram=timeline_diagram,
                hint="Ordne die Epochen von früh nach spät auf dem Zeitstrahl.",
                source="pedagogy",
            )
            items.insert(0, timeline_item)
            seen_prompts.add(str(timeline_item.get("prompt") or "").strip().lower())

    if _visual_tasks_have_label_placements(pedagogy):
        for task in pedagogy.get("visual_tasks") or []:
            if not isinstance(task, dict):
                continue
            if not is_label_format(str(task.get("kind") or "")):
                continue
            instruction = str(task.get("instruction") or "").strip()
            if instruction and (
                _UNUSABLE_VISUAL.search(instruction)
                or is_unusable_visual_instruction(instruction)
            ):
                continue
            placements = task.get("placements")
            if not isinstance(placements, list) or len(placements) < 3:
                continue
            if has_degenerate_placements(placements):
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
