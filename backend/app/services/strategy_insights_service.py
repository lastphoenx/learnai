"""Strategie-Trends aus App-Quiz und Lerntrainer (material-first)."""

from __future__ import annotations

import uuid
from collections import defaultdict

from sqlalchemy.orm import Session, joinedload

from app.ai.error_tags import infer_quiz_error_tags, label_for_tag
from app.ai.source_pedagogy import collect_pedagogy_from_unit_sources
from app.core.crypto import decrypt_text_master
from app.core.pedagogy_labels import material_labels_from_methods, normalize_label
from app.models import LearningRecord, LearningUnit
from app.services.crypto_json import decrypt_json


def _trend_key(label: str) -> str:
    return normalize_label(label) or label.strip().lower()


def _record_strategy_stats(
    stats: dict,
    *,
    unit: LearningUnit,
    material_labels: list[str],
    strategy_meta: dict[str, dict],
) -> None:
    from app.services.learn_service import is_quiz_selection_correct

    learn = stats.get("learn") if isinstance(stats.get("learn"), dict) else {}
    modules = sorted(unit.modules or [], key=lambda m: m.order_index)

    for module in modules:
        mod_key = str(module.id)
        mod_prog = (learn.get("modules") or {}).get(mod_key) or {}
        module_title = decrypt_text_master(module.title_encrypted)

        for ans in mod_prog.get("card_input_answers") or []:
            if not isinstance(ans, dict):
                continue
            method_label = str(ans.get("method_label") or "").strip()
            if not method_label:
                continue
            key = _trend_key(method_label)
            if not key:
                continue
            row = strategy_meta[key]
            row["label"] = method_label
            row["attempts"] += 1
            if ans.get("correct"):
                row["correct"] += 1
            row["unit_ids"].add(str(unit.id))
            row["sources"].add("trainer")

        answers = mod_prog.get("answers") or []
        quiz = decrypt_json(module.quiz_encrypted) or {}
        questions = quiz.get("questions") if isinstance(quiz, dict) else []
        if not isinstance(questions, list):
            questions = []

        for i, selected in enumerate(answers):
            if i >= len(questions) or selected is None:
                continue
            q = questions[i]
            if not isinstance(q, dict):
                continue
            if is_quiz_selection_correct(q, selected):
                continue
            error_keys = infer_quiz_error_tags(
                question=str(q.get("q", "")),
                module_title=module_title,
                explanation=str(q.get("explanation") or ""),
                material_labels=material_labels,
            )
            for error_key in error_keys:
                display = label_for_tag(error_key)
                key = _trend_key(display)
                if not key:
                    continue
                row = strategy_meta[key]
                row["label"] = display
                row["attempts"] += 1
                row["unit_ids"].add(str(unit.id))
                row["sources"].add("quiz")


def strategy_trends_for_profile(
    db: Session,
    tenant_id: uuid.UUID,
    profile_id: uuid.UUID,
    *,
    limit: int = 15,
) -> list[dict]:
    """Aggregiert Strategie-/Fehlermuster aus Quiz und Trainer über alle Einheiten."""
    records = (
        db.query(LearningRecord)
        .filter(LearningRecord.tenant_id == tenant_id, LearningRecord.profile_id == profile_id)
        .order_by(LearningRecord.last_activity_at.desc())
        .all()
    )
    strategy_meta: dict[str, dict] = defaultdict(
        lambda: {
            "label": "",
            "attempts": 0,
            "correct": 0,
            "unit_ids": set(),
            "sources": set(),
        }
    )

    unit_cache: dict[uuid.UUID, LearningUnit | None] = {}
    for rec in records:
        if not rec.unit_id:
            continue
        unit_id = rec.unit_id
        if unit_id not in unit_cache:
            unit_cache[unit_id] = (
                db.query(LearningUnit)
                .options(joinedload(LearningUnit.modules), joinedload(LearningUnit.sources))
                .filter(LearningUnit.id == unit_id, LearningUnit.tenant_id == tenant_id)
                .first()
            )
        unit = unit_cache[unit_id]
        if not unit or not unit.modules:
            continue
        stats = decrypt_json(rec.stats_encrypted) or {}
        from app.ai.subject_focus import detect_focus_group

        focus_group = detect_focus_group(subject=unit.subject, task_type=str(unit.task_type or ""))
        pedagogy = collect_pedagogy_from_unit_sources(unit.sources, focus_group=focus_group)
        material_labels = material_labels_from_methods(pedagogy.get("methods") or [])
        _record_strategy_stats(stats, unit=unit, material_labels=material_labels, strategy_meta=strategy_meta)

    rows: list[dict] = []
    for key, meta in strategy_meta.items():
        if meta["attempts"] <= 0:
            continue
        attempts = int(meta["attempts"])
        correct = int(meta["correct"])
        accuracy = round(100 * correct / attempts) if attempts else None
        rows.append(
            {
                "key": key,
                "label": meta["label"] or key,
                "attempts": attempts,
                "correct": correct,
                "accuracy": accuracy,
                "unit_count": len(meta["unit_ids"]),
                "sources": sorted(meta["sources"]),
            }
        )
    rows.sort(key=lambda row: (-row["attempts"], row["label"].lower()))
    return rows[:limit]
