"""Generische Grammatik-QA für generierte Lerneinheiten (Deutsch zuerst)."""

from __future__ import annotations

import logging
from typing import Any

from app.core.answer_match import text_answers_match
from app.core.focus_groups import normalize_focus_group
from app.core.german_case_analysis import (
    analyze_span_case_nested,
    case_from_label,
    case_label_de,
    get_case_check_spec,
    spacy_available,
    verify_case_answer_with_nesting,
    verify_case_label,
)
from app.core.german_declension import (
    cloze_answers_repairable,
    expected_blank_answers,
    parse_grammar_blanks,
    verify_cloze_answer,
)

_log = logging.getLogger(__name__)


def _given_answers(template: dict[str, Any]) -> list[str]:
    answers_raw = template.get("answers")
    if answers_raw is None:
        return []
    if isinstance(answers_raw, str):
        return [part.strip() for part in answers_raw.split("|")]
    if isinstance(answers_raw, list):
        return [str(a).strip() for a in answers_raw]
    return []


def verify_german_cloze_template(template: dict[str, Any]) -> tuple[bool, str | None]:
    """Prüft cloze_template mit grammar.blanks — deterministisch wie Mathe-Nachrechnen."""
    grammar = template.get("grammar")
    if not isinstance(grammar, dict):
        return True, None
    blanks = parse_grammar_blanks(grammar.get("blanks"))
    if not blanks:
        return True, None
    given = _given_answers(template)
    if len(given) != len(blanks):
        return False, "grammar.blanks vorhanden, aber keine answers"
    given_joined = "|".join(given)
    if verify_cloze_answer(blanks=blanks, given_answer=given):
        return True, None
    expected = expected_blank_answers(blanks)
    return False, f"Erwartet {'|'.join(expected)}, erhalten {given_joined}"


def repair_german_cloze_template(template: dict[str, Any]) -> dict[str, Any]:
    """Setzt answers aus der Engine, wenn grammar.blanks vorhanden (KI nur Struktur)."""
    grammar = template.get("grammar")
    if not isinstance(grammar, dict):
        return template
    blanks = parse_grammar_blanks(grammar.get("blanks"))
    if not blanks:
        return template
    repaired = dict(template)
    repaired["answers"] = expected_blank_answers(blanks)
    return repaired


def verify_card_case_label_with_nesting(
    *,
    expected: str,
    given: str,
    sentence: str,
    span: str,
) -> str:
    """Prüft Fall-Antwort inkl. «Teilrichtig, falsche Ebene»."""
    return verify_case_answer_with_nesting(
        expected_answer=expected,
        given_answer=given,
        sentence=sentence,
        span=span,
    )


def _nested_case_metadata(card: dict[str, Any]) -> list[dict[str, str]] | None:
    spec = get_case_check_spec(card)
    if not spec:
        return None
    analysis = analyze_span_case_nested(sentence=spec["sentence"], span=spec["span"])
    if analysis.get("confidence") != "high":
        return None
    nested = analysis.get("nested") or []
    if not nested:
        return None
    return [{"text": text, "case": case} for text, case in nested]


def enrich_german_case_card(card: dict[str, Any]) -> dict[str, Any]:
    """Hängt erkannte eingebettete Fälle an grammar.case_check."""
    nested_meta = _nested_case_metadata(card)
    if not nested_meta:
        return card
    enriched = dict(card)
    grammar = dict(enriched.get("grammar") or {})
    case_check = dict(grammar.get("case_check") or {})
    spec = get_case_check_spec(card)
    if spec:
        case_check.setdefault("sentence", spec["sentence"])
        case_check.setdefault("span", spec["span"])
    case_check["nested"] = nested_meta
    grammar["case_check"] = case_check
    enriched["grammar"] = grammar
    return enriched


def verify_card_case_label(card: dict[str, Any]) -> tuple[str | None, str | None]:
    """Prüft Fall-Karte gegen spaCy.

    Returns:
        (level, message) — level: ok | warn | info | None (nicht prüfbar)
    """
    spec = get_case_check_spec(card)
    if not spec:
        return None, None
    answer = str(card.get("answer") or "")
    expected_case = case_from_label(answer)
    if not expected_case:
        return "warn", f"Antwort «{answer[:40]}» ist kein Fall-Label"
    match, result = verify_case_label(
        expected_answer=answer,
        sentence=spec["sentence"],
        span=spec["span"],
    )
    span = spec["span"]
    if result.confidence == "unavailable":
        return "info", f"«{span}»: spaCy nicht verfügbar — gespeichert {case_label_de(expected_case)}"
    if match is True:
        return "ok", f"«{span}»: {case_label_de(expected_case)} (spaCy bestätigt)"
    if match is False:
        return (
            "warn",
            f"«{span}»: gespeichert {case_label_de(expected_case)}, "
            f"spaCy {case_label_de(result.case)} ({result.detail})",
        )
    return "info", f"«{span}»: gespeichert {case_label_de(expected_case)}, spaCy ohne sicheres Case"


def verify_basiswissen_grammar(basiswissen: dict[str, Any]) -> list[str]:
    """Sammelt Grammatik-Warnungen für ein Basiswissen-Objekt."""
    warnings: list[str] = []
    group = normalize_focus_group(str(basiswissen.get("focus_group") or ""))
    if group != "german":
        return warnings
    for template in basiswissen.get("cloze_templates") or []:
        if not isinstance(template, dict):
            continue
        ok, reason = verify_german_cloze_template(template)
        if not ok:
            tid = template.get("id") or "?"
            warnings.append(f"Cloze {tid}: {reason}")
    return warnings


def repair_basiswissen_grammar(basiswissen: dict[str, Any]) -> dict[str, Any]:
    """Repariert Antworten aus der Engine; verwirft unprüfbare grammar-Clozes."""
    group = normalize_focus_group(str(basiswissen.get("focus_group") or ""))
    if group != "german":
        return basiswissen
    repaired = dict(basiswissen)
    templates: list[dict[str, Any]] = []
    for raw in basiswissen.get("cloze_templates") or []:
        if not isinstance(raw, dict):
            continue
        grammar = raw.get("grammar")
        if not isinstance(grammar, dict) or not parse_grammar_blanks(grammar.get("blanks")):
            templates.append(raw)
            continue
        fixed = repair_german_cloze_template(raw)
        blanks = parse_grammar_blanks(grammar.get("blanks"))
        answers = fixed.get("answers") or []
        ok, reason = cloze_answers_repairable(blanks, list(answers))
        if not ok:
            _log.warning(
                "repair_basiswissen drop cloze id=%s reason=%s",
                raw.get("id") or "?",
                reason,
            )
            continue
        templates.append(fixed)
    repaired["cloze_templates"] = templates
    return repaired


def finalize_german_cards(
    cards: list[dict[str, Any]],
    *,
    focus_group: str,
) -> list[dict[str, Any]]:
    kept, _drops = finalize_german_cards_with_drops(cards, focus_group=focus_group)
    return kept


def finalize_german_cards_with_drops(
    cards: list[dict[str, Any]],
    *,
    focus_group: str,
    difficulty: int = 3,
) -> tuple[list[dict[str, Any]], list[str]]:
    """Verwirft Fall-Karten mit hochkonfidenter spaCy-Abweichung; liefert Drop-Gründe."""
    group = normalize_focus_group(focus_group)
    if group != "german":
        return cards, []
    kept: list[dict[str, Any]] = []
    dropped: list[str] = []
    max_difficulty_for_nested = 2
    for card in cards:
        if not isinstance(card, dict):
            continue
        nested_meta = _nested_case_metadata(card)
        if nested_meta and difficulty <= max_difficulty_for_nested:
            spec = get_case_check_spec(card) or {}
            span = spec.get("span", "?")
            question = str(card.get("question") or "")[:80]
            dropped.append(f"{question!r}: «{span}» enthält verschachtelte Fälle (Stufe {difficulty})")
            continue
        level, msg = verify_card_case_label(card)
        if level == "warn":
            match, result = verify_case_label(
                expected_answer=str(card.get("answer") or ""),
                sentence=(get_case_check_spec(card) or {}).get("sentence", ""),
                span=(get_case_check_spec(card) or {}).get("span", ""),
            )
            if match is False and result.confidence == "high":
                question = str(card.get("question") or "")[:80]
                dropped.append(f"{question!r}: {msg}")
                continue
        out = enrich_german_case_card(card) if nested_meta else card
        kept.append(out)
    return kept, dropped


def collect_grammar_warnings_for_module(
    *,
    content: dict[str, Any],
    quiz: dict[str, Any] | None = None,
    focus_group: str,
) -> list[dict[str, str]]:
    """Sammelt strukturierte Grammatik-Hinweise für Qualitätsreport und Admin."""
    group = normalize_focus_group(focus_group)
    if group != "german":
        return []
    warnings: list[dict[str, str]] = []
    basiswissen = content.get("basiswissen") if isinstance(content, dict) else None
    if isinstance(basiswissen, dict):
        for msg in verify_basiswissen_grammar(basiswissen):
            warnings.append({"kind": "declension", "level": "warn", "ref": "basiswissen", "message": msg})
        for template in basiswissen.get("cloze_templates") or []:
            if isinstance(template, dict) and isinstance(template.get("grammar"), dict):
                tid = str(template.get("id") or "?")
                warnings.append(
                    {
                        "kind": "declension",
                        "level": "ok",
                        "ref": f"cloze:{tid}",
                        "message": f"Cloze {tid}: Deklination engine-geprüft",
                    }
                )
    cards = content.get("cards") if isinstance(content, dict) else []
    if isinstance(cards, list):
        for index, card in enumerate(cards, start=1):
            if not isinstance(card, dict):
                continue
            kind = str(card.get("kind") or "mental")
            ref = f"K{index:02d}:{kind}"
            level, message = verify_card_case_label(card)
            if level and message:
                warnings.append(
                    {
                        "kind": "case",
                        "level": level,
                        "ref": ref,
                        "message": message,
                    }
                )
            grammar = card.get("grammar")
            if isinstance(grammar, dict) and parse_grammar_blanks((grammar.get("blanks") or [])):
                warnings.append(
                    {
                        "kind": "declension",
                        "level": "ok",
                        "ref": ref,
                        "message": f"Karte {ref}: Deklination engine-geprüft",
                    }
                )
    return warnings


def summarize_grammar_warnings(warnings: list[dict[str, str]]) -> dict[str, Any]:
    counts = {"ok": 0, "warn": 0, "info": 0, "declension": 0, "case": 0}
    for item in warnings:
        level = str(item.get("level") or "")
        if level in counts:
            counts[level] += 1
        kind = str(item.get("kind") or "")
        if kind in counts:
            counts[kind] += 1
    return {
        "total": len(warnings),
        "ok": counts["ok"],
        "warn": counts["warn"],
        "info": counts["info"],
        "declension_checks": counts["declension"],
        "case_checks": counts["case"],
        "spacy_available": spacy_available(),
    }


def format_grammar_report_section(warnings: list[dict[str, str]]) -> list[str]:
    """Markdown-Zeilen für unit_quality_report."""
    if not warnings:
        return ["_Keine Deutsch-Grammatik-Prüfungen (Fachgruppe nicht «german» oder kein prüfbares Material)._", ""]
    summary = summarize_grammar_warnings(warnings)
    lines = [
        f"- spaCy: {'verfügbar' if summary['spacy_available'] else 'nicht verfügbar (Fallprüfung eingeschränkt)'}",
        f"- Geprüft: {summary['total']} Einträge · OK {summary['ok']} · "
        f"Warnungen {summary['warn']} · Hinweise {summary['info']}",
        "",
    ]
    decl = [w for w in warnings if w.get("kind") == "declension"]
    case = [w for w in warnings if w.get("kind") == "case"]
    if decl:
        lines.append("**Deklination (deterministisch)**")
        for item in decl:
            mark = {"ok": "✓", "warn": "⚠", "info": "·"}.get(str(item.get("level")), "-")
            lines.append(f"- {mark} [{item.get('ref')}] {item.get('message')}")
        lines.append("")
    if case:
        lines.append("**Fallbestimmung (spaCy — Zusatzsignal, kein absolutes Gate)**")
        for item in case:
            mark = {"ok": "✓", "warn": "⚠", "info": "·"}.get(str(item.get("level")), "-")
            lines.append(f"- {mark} [{item.get('ref')}] {item.get('message')}")
        lines.append("")
    return lines


def verify_short_text_case_answer(
    *,
    expected: str,
    user_answer: str,
    sentence: str | None = None,
    span: str | None = None,
    nested: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    """Fall-Labels — inkl. «Teilrichtig, falsche Ebene» bei verschachtelten Fällen."""
    if text_answers_match(expected, user_answer):
        return {"outcome": "correct", "partial": False, "feedback": None}
    if sentence and span:
        outcome = verify_case_answer_with_nesting(
            expected_answer=expected,
            given_answer=user_answer,
            sentence=sentence,
            span=span,
        )
        if outcome == "teilrichtig_falsche_ebene":
            given_case = case_from_label(user_answer)
            expected_case = case_from_label(expected)
            nested_hit = None
            for item in nested or []:
                if case_from_label(str(item.get("case") or "")) == given_case:
                    nested_hit = item
                    break
            if nested_hit is None:
                analysis = analyze_span_case_nested(sentence=sentence, span=span)
                for text, nested_case in analysis.get("nested") or []:
                    if nested_case == given_case:
                        nested_hit = {"text": text, "case": nested_case}
                        break
            nested_text = str((nested_hit or {}).get("text") or "ein Teil").strip()
            feedback = (
                f"Fast richtig gedacht! «{nested_text}» ist tatsächlich "
                f"{case_label_de(given_case)} — gesucht war aber der Fall der "
                f"ganzen Wortgruppe «{span}»: {case_label_de(expected_case)}."
            )
            return {"outcome": "teilrichtig_falsche_ebene", "partial": True, "feedback": feedback}
        if outcome == "correct":
            return {"outcome": "correct", "partial": False, "feedback": None}
    return {"outcome": "wrong", "partial": False, "feedback": None}
