"""Qualitätsreport für Lerneinheiten (Referenz 0001 / 0001.0001)."""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session, joinedload

from app.ai.source_pedagogy import build_pedagogy_digest, collect_pedagogy_from_unit_sources
from app.core.crypto import decrypt_text_master
from app.core.quiz_explanation import enrich_quiz_explanation, explanation_is_weak
from app.models import LearningRecord, LearningUnit, User
from app.services.crypto_json import decrypt_json
from app.services.learn_service import learn_progress_for_unit
from app.services.pedagogy_service import _pedagogy_quality
from app.services.unit_reference_service import (
    UnitReferenceError,
    ensure_unit_reference_codes,
    find_units_by_reference,
)
from app.services.unit_service import UnitError, get_learn_goals, get_trainer_options


def _quiz_lines(quiz: dict, *, module_ref: str) -> list[str]:
    lines: list[str] = []
    questions = quiz.get("questions") if isinstance(quiz, dict) else []
    if not isinstance(questions, list):
        return lines
    for qi, question in enumerate(questions, start=1):
        if not isinstance(question, dict):
            continue
        qtext = str(question.get("q") or "").strip()
        options = question.get("options") or []
        answer = question.get("answer")
        explanation = str(question.get("explanation") or "").strip()
        qtype = str(question.get("question_type") or "").strip()
        method_id = str(question.get("method_id") or question.get("method_label") or "").strip()
        shown = enrich_quiz_explanation(question)
        lines.append(f"#### Quiz {module_ref}.{qi:02d}")
        if qtype:
            lines.append(f"- Typ: {qtype}")
        if method_id:
            lines.append(f"- Methode: {method_id}")
        lines.append(f"- Frage: {qtext}")
        if isinstance(options, list):
            for oi, opt in enumerate(options):
                mark = " ✓" if answer == oi else ""
                lines.append(f"  - [{chr(65 + oi)}]{mark} {opt}")
        if qtype != "method" and explanation and explanation_is_weak(explanation, qtext):
            lines.append("- Warnung: gespeicherte Erklärung ohne ausgerechnete Zwischenschritte (Rezept).")
        if shown:
            lines.append(f"- Erklärung: {shown}")
        lines.append("")
    return lines


def _card_lines(content: dict, *, module_ref: str) -> list[str]:
    lines: list[str] = []
    cards = content.get("cards") if isinstance(content, dict) else []
    if not isinstance(cards, list):
        return lines
    for ci, card in enumerate(cards, start=1):
        if not isinstance(card, dict):
            continue
        kind = str(card.get("kind") or "mental")
        lines.append(f"#### Karte {module_ref}.K{ci:02d} ({kind})")
        lines.append(f"- Frage: {card.get('question', '')}")
        lines.append(f"- Antwort: {card.get('answer', '')}")
        if card.get("tip"):
            lines.append(f"- Tipp: {card.get('tip')}")
        if card.get("method_label"):
            lines.append(f"- Methode: {card.get('method_label')}")
        if card.get("expected_method"):
            lines.append(f"- Erwartete Methode: {card.get('expected_method')}")
        lines.append("")
    return lines


def _module_section(unit: LearningUnit, *, family: str, instance: str) -> list[str]:
    lines: list[str] = []
    modules = sorted(unit.modules or [], key=lambda m: m.order_index)
    if not modules:
        status = str(unit.status or "").strip() or "unbekannt"
        return [
            f"_Keine Module auf dieser Instanz (Status: {status} — noch nicht generiert oder draft)._",
            "",
        ]
    for mod in modules:
        order = mod.order_index + 1
        module_ref = f"{family}.{order:02d}"
        title = decrypt_text_master(mod.title_encrypted)
        lines.append(f"### Modul {module_ref}: {title}")
        content = decrypt_json(mod.content_encrypted) or {}
        quiz = decrypt_json(mod.quiz_encrypted) or {}
        if isinstance(content, dict) and content.get("intro"):
            lines.append(f"- Intro: {str(content.get('intro'))[:400]}")
        if isinstance(content, dict) and content.get("knowledge"):
            lines.append(f"- Wissenspunkte: {len(content.get('knowledge') or [])}")
        lines.extend(_card_lines(content if isinstance(content, dict) else {}, module_ref=module_ref))
        lines.extend(_quiz_lines(quiz if isinstance(quiz, dict) else {}, module_ref=module_ref))
    return lines


def _pedagogy_section(unit: LearningUnit) -> list[str]:
    profile = collect_pedagogy_from_unit_sources(unit.sources)
    if not profile.get("methods") and not profile.get("exercise_patterns"):
        return ["_Keine strukturierte Didaktik in den Quellen._", ""]
    quality = _pedagogy_quality(profile)
    lines = [
        f"- Qualität: {quality.get('level')} ({quality.get('method_count')} Strategien)",
        "",
        "**Strategien / Lösungswege:**",
    ]
    for method in profile.get("methods") or []:
        if not isinstance(method, dict):
            continue
        label = method.get("label") or "?"
        when = method.get("when") or ""
        example = method.get("example") or ""
        lines.append(f"- **{label}** — {when}")
        if example:
            lines.append(f"  - Beispiel: {example}")
    patterns = profile.get("exercise_patterns") or []
    if patterns:
        lines.append("")
        lines.append("**Aufgabentypen:** " + " · ".join(str(p) for p in patterns))
    digest = build_pedagogy_digest(profile)
    if digest:
        lines.extend(["", "**Digest:**", "```", digest[:2000], "```"])
    return lines


def _progress_section(db: Session, unit: LearningUnit, record: LearningRecord) -> list[str]:
    prog = learn_progress_for_unit(db, unit.id)
    lines: list[str] = []
    if prog:
        lines.append(
            f"- Status: {prog.get('status')} · {prog.get('percent', 0)}% · "
            f"Quiz {prog.get('quiz_correct', 0)}/{prog.get('quiz_total', 0)}"
        )
    stats = decrypt_json(record.stats_encrypted) if record.stats_encrypted else {}
    learn = stats.get("learn") if isinstance(stats, dict) else {}
    if not isinstance(learn, dict):
        return lines
    modules_stats = learn.get("modules") or {}
    if not modules_stats:
        lines.append("- Noch keine Modul-Antworten gespeichert.")
        return lines
    lines.append("")
    lines.append("**Quiz-Antworten (Instanz):**")
    for module in sorted(unit.modules or [], key=lambda m: m.order_index):
        mid = str(module.id)
        mod_stats = modules_stats.get(mid) or modules_stats.get(module.id)
        if not isinstance(mod_stats, dict):
            continue
        title = decrypt_text_master(module.title_encrypted)
        lines.append(f"- **{title}**")
        details = mod_stats.get("answer_details") or {}
        if isinstance(details, dict):
            for key, detail in sorted(details.items(), key=lambda kv: int(kv[0]) if str(kv[0]).isdigit() else 0):
                if not isinstance(detail, dict):
                    continue
                sel = detail.get("selected")
                correct = detail.get("correct")
                lines.append(
                    f"  - Frage {int(key) + 1}: gewählt={sel!r} "
                    f"{'✓' if correct else '✗'} — {detail.get('explanation', '')[:120]}"
                )
    return lines


def _unit_header(unit: LearningUnit, record: LearningRecord, refs: dict) -> list[str]:
    title = decrypt_text_master(unit.title_encrypted)
    learner = unit.profile.display_name if unit.profile else "—"
    recon = decrypt_json(record.reconstruction_encrypted) if record.reconstruction_encrypted else {}
    math_focus = ""
    if isinstance(recon, dict):
        math_focus = str(recon.get("math_focus") or "").strip()
    lines = [
        f"- Referenz: **{refs.get('reference_code') or '—'}** (Familie {refs.get('reference_family')})",
        f"- UUID: `{unit.id}`",
        f"- Titel: {title}",
        f"- Fach: {unit.subject or '—'}",
        f"- Modus: {unit.task_type or 'mixed'}",
        f"- Schwierigkeit: {unit.difficulty}",
        f"- Status: {unit.status}",
        f"- Lerner: {learner}",
    ]
    if math_focus:
        lines.append(f"- Schwerpunkt: {math_focus}")
    if unit.task_type == "interactive" and isinstance(recon, dict):
        goals = get_learn_goals(recon)
        opts = get_trainer_options(recon)
        lines.append(f"- Trainer: {opts.get('cards')} Karten / {opts.get('questions')} Quiz · Stil {opts.get('style')}")
        if goals.get("enabled"):
            lines.append(f"- Lernziele aktiv: {goals}")
    return lines


def build_unit_quality_report(db: Session, user: User, ref: str) -> dict:
    family, instance, matches = find_units_by_reference(db, user.tenant_id, ref)
    scope = "instance" if instance else "family"

    lines: list[str] = [
        f"# LearnAI Qualitätsreport — {ref}",
        "",
        f"**Umfang:** {'Instanz (ein Kind/eine Kopie)' if scope == 'instance' else 'Familie (alle Kopien)'}",
        f"**Tenant:** `{user.tenant_id}`",
        "",
    ]

    if scope == "family":
        lines.append("## Instanzen in dieser Familie")
        lines.append("")
        for unit, record in matches:
            refs = ensure_unit_reference_codes(db, unit, record, persist=False)
            title = decrypt_text_master(unit.title_encrypted)
            learner = unit.profile.display_name if unit.profile else "—"
            lines.append(
                f"- `{refs.get('reference_code')}` — {title} ({learner}) · {unit.status} · "
                f"{len(unit.modules or [])} Module"
            )
        lines.append("")
        root_unit, root_record = matches[0]
        lines.append("## Inhalt (Vorlage — älteste Instanz der Familie)")
        lines.append("")
        refs = ensure_unit_reference_codes(db, root_unit, root_record, persist=False)
        lines.extend(_unit_header(root_unit, root_record, refs))
        lines.append("")
        lines.append("## Didaktik aus Quellen")
        lines.append("")
        root_loaded = (
            db.query(LearningUnit)
            .options(joinedload(LearningUnit.modules), joinedload(LearningUnit.sources), joinedload(LearningUnit.profile))
            .filter(LearningUnit.id == root_unit.id)
            .first()
        )
        if root_loaded:
            lines.extend(_pedagogy_section(root_loaded))
            lines.append("")
            lines.append("## Module, Karten & Quiz (Lösungsvarianten)")
            lines.append("")
            fam = refs.get("reference_family") or family
            inst = refs.get("reference_instance") or "0001"
            lines.extend(_module_section(root_loaded, family=fam, instance=inst))
    else:
        unit, record = matches[0]
        unit = (
            db.query(LearningUnit)
            .options(joinedload(LearningUnit.modules), joinedload(LearningUnit.sources), joinedload(LearningUnit.profile))
            .filter(LearningUnit.id == unit.id)
            .first()
        ) or unit
        refs = ensure_unit_reference_codes(db, unit, record, persist=False)
        lines.append("## Einheit")
        lines.append("")
        lines.extend(_unit_header(unit, record, refs))
        lines.append("")
        lines.append("## Didaktik aus Quellen")
        lines.append("")
        lines.extend(_pedagogy_section(unit))
        lines.append("")
        lines.append("## Module, Karten & Quiz (Lösungsvarianten)")
        lines.append("")
        fam = refs.get("reference_family") or family
        inst = refs.get("reference_instance") or instance or "0001"
        lines.extend(_module_section(unit, family=fam, instance=inst))
        lines.append("## Lernfortschritt dieser Instanz")
        lines.append("")
        lines.extend(_progress_section(db, unit, record))

    report = "\n".join(lines).strip() + "\n"
    return {
        "ref": ref,
        "scope": scope,
        "family": family,
        "instance": instance,
        "unit_count": len(matches),
        "report": report,
        "ok": True,
    }


def build_unit_quality_report_for_user(db: Session, user: User, ref: str) -> dict:
    try:
        return build_unit_quality_report(db, user, ref)
    except UnitReferenceError as exc:
        raise UnitError(exc.message, exc.code) from exc
