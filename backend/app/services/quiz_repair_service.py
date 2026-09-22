"""Quiz-Inhalt in gespeicherten Modulen reparieren (Referenz-Slots, Familie)."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.quiz_content_patches import apply_manual_quiz_patch, parse_quiz_slot_ref
from app.core.quiz_numeric import repair_quiz_block
from app.models import LearningUnit, UnitModule, User
from app.services.crypto_json import decrypt_json, encrypt_json
from app.services.unit_reference_service import ensure_unit_reference_codes, find_units_by_reference


def _module_order(mod: UnitModule) -> int:
    return int(mod.order_index) + 1


def repair_quiz_slot_in_module(
    mod: UnitModule,
    *,
    module_order: int,
    question_no: int,
    family: str,
    dry_run: bool,
) -> dict | None:
    if _module_order(mod) != module_order:
        return None
    quiz = decrypt_json(mod.quiz_encrypted) or {}
    if not isinstance(quiz, dict):
        return None
    questions = quiz.get("questions")
    if not isinstance(questions, list):
        return None
    qi = question_no - 1
    if qi < 0 or qi >= len(questions):
        return None
    raw = questions[qi]
    if not isinstance(raw, dict):
        return None

    slot_ref = f"{family}.{module_order:02d}.{question_no:02d}"
    before = dict(raw)
    patched = apply_manual_quiz_patch(before, slot_ref)
    repaired_block = repair_quiz_block({"questions": [patched]})
    after = (repaired_block.get("questions") or [None])[0]
    if not isinstance(after, dict):
        return None
    if after == before:
        return {"slot": slot_ref, "changed": False, "before": before, "after": after}

    if not dry_run:
        questions = list(questions)
        questions[qi] = after
        quiz = dict(quiz)
        quiz["questions"] = questions
        mod.quiz_encrypted = encrypt_json(quiz)

    return {"slot": slot_ref, "changed": True, "before": before, "after": after}


def repair_quiz_slot_for_reference(
    db: Session,
    user: User,
    ref: str,
    *,
    dry_run: bool = True,
) -> list[dict]:
    family, module_order, question_no = parse_quiz_slot_ref(ref)
    _, instance, matches = find_units_by_reference(db, user.tenant_id, family)
    results: list[dict] = []
    for unit, record in matches:
        refs = ensure_unit_reference_codes(db, unit, record, persist=False)
        code = refs.get("reference_code") or "—"
        for mod in sorted(unit.modules or [], key=lambda m: m.order_index):
            row = repair_quiz_slot_in_module(
                mod,
                module_order=module_order,
                question_no=question_no,
                family=family,
                dry_run=dry_run,
            )
            if row:
                row["unit_id"] = str(unit.id)
                row["reference_code"] = code
                results.append(row)
    if not dry_run:
        db.flush()
    return results


def repair_all_quizzes_in_family(
    db: Session,
    user: User,
    family_ref: str,
    *,
    dry_run: bool = True,
) -> int:
    """Alle Quiz-Fragen einer Familie durch repair_quiz_block laufen lassen."""
    family, instance, matches = find_units_by_reference(db, user.tenant_id, family_ref)
    if instance:
        raise ValueError("Nur Familien-Referenz (z. B. 0036), nicht Instanz")
    changed = 0
    for unit, record in matches:
        ensure_unit_reference_codes(db, unit, record, persist=False)
        for mod in unit.modules or []:
            quiz = decrypt_json(mod.quiz_encrypted) or {}
            if not isinstance(quiz, dict):
                continue
            before = quiz
            repaired = repair_quiz_block(quiz)
            if repaired == before:
                continue
            changed += 1
            if not dry_run:
                mod.quiz_encrypted = encrypt_json(repaired)
    if not dry_run:
        db.flush()
    return changed
