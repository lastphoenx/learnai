"""Inhalts-QA: generische Texte, mehrdeutige Concept-Fragen, Platzhalter-Übungen."""

from __future__ import annotations

import re
from collections import Counter
from difflib import SequenceMatcher
from typing import Any

_AMBIGUOUS_CONCEPT_Q = re.compile(
    r"Welcher Begriff passt bei .+\?\s*\(Muster:.+\)",
    re.I,
)
_GENERIC_CASE_EXPL = re.compile(
    r"Fälle zeigen,.+W-Fragen findest",
    re.I | re.S,
)
_MENTAL_TERM_Q = re.compile(r"Was bedeutet «([^»]+)»")
_CASE_ONLY_ANSWER = re.compile(
    r"^(nominativ|genitiv|dativ|akkusativ|nom\.?|gen\.?|dat\.?|akk\.?)$",
    re.I,
)


def _is_case_label_answer(answer: str) -> bool:
    primary = str(answer or "").split("|")[0].strip()
    return bool(_CASE_ONLY_ANSWER.match(primary))


def _mental_term_from_question(question: str) -> str:
    match = _MENTAL_TERM_Q.search(question)
    return match.group(1).strip() if match else ""


def _strip_leading_term_prefix(answer: str, term: str) -> str:
    text = answer.strip()
    if not term:
        return text.lower()
    prefix = term.strip()
    if text.lower().startswith(prefix.lower()):
        rest = text[len(prefix) :].lstrip()
        if rest[:1] in {":", "—", "-"}:
            rest = rest[1:].lstrip()
        return rest.lower()
    return text.lower()


def _near_duplicate_bodies(bodies: list[str], *, ratio: float = 0.88) -> int:
    """Grösste Gruppe inhaltlich (fast) gleicher Antwort-Körper."""
    if len(bodies) < 2:
        return len(bodies)
    groups: list[list[str]] = []
    for body in bodies:
        placed = False
        for group in groups:
            if SequenceMatcher(None, body, group[0]).ratio() >= ratio:
                group.append(body)
                placed = True
                break
        if not placed:
            groups.append([body])
    return max(len(group) for group in groups)


def collect_content_warnings_for_module(
    *,
    content: dict | None,
    quiz: dict | None,
    focus_group: str = "general",
) -> list[dict[str, str]]:
    warnings: list[dict[str, str]] = []
    content = content if isinstance(content, dict) else {}
    quiz = quiz if isinstance(quiz, dict) else {}

    answer_by_question: dict[str, str] = {}
    for card in content.get("cards") or []:
        if not isinstance(card, dict):
            continue
        q = str(card.get("question") or "").strip().lower()
        a = str(card.get("answer") or "").strip()
        if not q or not a:
            continue
        prev = answer_by_question.get(q)
        if prev and prev != a:
            warnings.append(
                {
                    "kind": "duplicate_card_answer",
                    "level": "warn",
                    "ref": "card",
                    "message": f"Gleiche Kartenfrage, unterschiedliche Antworten: «{q[:60]}…»",
                }
            )
        answer_by_question.setdefault(q, a)

    answers_seen: dict[str, list[str]] = {}
    mental_bodies: list[str] = []
    for card in content.get("cards") or []:
        if not isinstance(card, dict):
            continue
        q = str(card.get("question") or "").strip()
        a = str(card.get("answer") or "").strip()
        if not q or not a:
            continue
        answers_seen.setdefault(a, []).append(q)

        kind = str(card.get("kind") or "mental").strip().lower()
        card_role = str(card.get("card_role") or "").strip().lower()
        track_body = (
            card_role in {"term", "cloze"}
            or kind == "mental"
            or _MENTAL_TERM_Q.search(q) is not None
        )
        if not track_body:
            continue
        term = _mental_term_from_question(q) if _MENTAL_TERM_Q.search(q) else ""
        body = _strip_leading_term_prefix(a, term) if term else a.lower()
        if len(body) >= 12:
            mental_bodies.append(body)
    group = str(focus_group or "general").strip().lower()
    for answer, questions in answers_seen.items():
        if group == "german" and _is_case_label_answer(answer):
            continue
        if len(questions) >= 3 and len({q.split("«")[1].split("»")[0] if "«" in q else q for q in questions}) >= 3:
            warnings.append(
                {
                    "kind": "generic_mental_cards",
                    "level": "warn",
                    "ref": "cards",
                    "message": (
                        f"{len(questions)} Kurzkarten teilen dieselbe Antwort "
                        f"(«{answer[:80]}…») — vermutlich generischer Textbaustein."
                    ),
                }
            )
    if len(mental_bodies) >= 3:
        exact_dupes = Counter(mental_bodies).most_common(1)[0][1]
        near_dupes = _near_duplicate_bodies(mental_bodies)
        dup_count = max(exact_dupes, near_dupes)
        if dup_count >= 3:
            warnings.append(
                {
                    "kind": "generic_mental_cards",
                    "level": "warn",
                    "ref": "cards",
                    "message": (
                        f"{dup_count} Mental-Karten haben (fast) identischen Erklärtext "
                        "— nur der Begriff unterscheidet sich."
                    ),
                }
            )

    expl_by_text: dict[str, list[str]] = {}
    for qi, question in enumerate(quiz.get("questions") or []):
        if not isinstance(question, dict):
            continue
        qtext = str(question.get("q") or "").strip()
        expl = str(question.get("explanation") or "").strip()
        ref = f"quiz/{qi + 1}"
        if _AMBIGUOUS_CONCEPT_Q.search(qtext):
            warnings.append(
                {
                    "kind": "ambiguous_concept_question",
                    "level": "warn",
                    "ref": ref,
                    "message": "Mehrdeutige Concept-Frage (Muster listet mehrere Begriffe gleichwertig).",
                }
            )
        target = str(question.get("target_term") or "").strip()
        if str(question.get("question_type") or "") == "concept" and expl:
            if target and target.lower() not in expl.lower() and "richtig" not in expl.lower():
                warnings.append(
                    {
                        "kind": "weak_concept_explanation",
                        "level": "info",
                        "ref": ref,
                        "message": f"Erklärung nennt «{target}» nicht — vermutlich generischer Text.",
                    }
                )
            if _GENERIC_CASE_EXPL.search(expl):
                warnings.append(
                    {
                        "kind": "generic_case_explanation",
                        "level": "warn",
                        "ref": ref,
                        "message": "Generische Fall-Erklärung ohne Bezug zur konkreten Aufgabe.",
                    }
                )
        if expl:
            expl_by_text.setdefault(expl, []).append(ref)
    for expl, refs in expl_by_text.items():
        if len(refs) >= 2 and len(expl) >= 60:
            warnings.append(
                {
                    "kind": "duplicate_quiz_explanation",
                    "level": "warn",
                    "ref": refs[0],
                    "message": f"Identische Erklärung in {len(refs)} Quizfragen.",
                }
            )

    group = str(focus_group or "general").strip().lower()
    for pi, item in enumerate(content.get("practice") or []):
        if not isinstance(item, dict):
            continue
        if str(item.get("answer_type") or "") != "label_diagram":
            continue
        diagram = item.get("diagram") if isinstance(item.get("diagram"), dict) else {}
        if diagram.get("template") == "generic" and group == "german":
            src = str(item.get("source") or "")
            warnings.append(
                {
                    "kind": "generic_label_diagram",
                    "level": "warn",
                    "ref": f"practice/{pi + 1}",
                    "message": (
                        "Bild-Beschriftung ohne echtes Bild (generisches Rad) — "
                        f"didaktisch fragwürdig (Quelle: {src or '?'})."
                    ),
                }
            )

    return warnings


def summarize_content_warnings(warnings: list[dict[str, str]]) -> dict[str, Any]:
    total = len(warnings)
    warn = sum(1 for w in warnings if w.get("level") == "warn")
    info = sum(1 for w in warnings if w.get("level") == "info")
    return {"total": total, "warn": warn, "info": info}
