"""Offline-Export/Import für interaktive Lerntrainer (LearnAI + Bio-Ranger JSON)."""

from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.crypto import decrypt_text_master, encrypt_text_master
from app.models import LearningRecord, LearningUnit, UnitModule, User
from app.services.crypto_json import decrypt_json, encrypt_json
from app.ai.quiz_shuffle import shuffle_quiz_block
from app.core.quiz_numeric import repair_quiz_block
from app.ai.validators.interactive import validate_interactive_import
from app.services.unit_service import (
    UnitError,
    _dec_module,
    _dec_unit,
    _get_unit_or_404,
    create_unit,
    get_trainer_options,
)

EXPORT_FORMAT = "learnai-trainer-v1"


def _slug_filename(title: str) -> str:
    base = re.sub(r"[^\w\s-]", "", title, flags=re.UNICODE).strip().lower()
    base = re.sub(r"[-\s]+", "-", base).strip("-") or "trainer"
    return f"{base[:60]}.json"


def _bio_ranger_block(modules: list[dict], *, title: str) -> dict:
    cards: list[dict] = []
    questions: list[dict] = []
    tips: list[str] = []
    for mod in modules:
        content = mod.get("content") if isinstance(mod.get("content"), dict) else {}
        for card in content.get("cards") or []:
            if not isinstance(card, dict):
                continue
            tip = str(card.get("tip") or "").strip()
            cards.append(
                {
                    "q": str(card.get("question") or ""),
                    "a": str(card.get("answer") or ""),
                    "tip": tip,
                }
            )
            if tip:
                tips.append(tip)
        quiz = mod.get("quiz") if isinstance(mod.get("quiz"), dict) else {}
        for q in quiz.get("questions") or []:
            if not isinstance(q, dict):
                continue
            questions.append(
                {
                    "q": str(q.get("q") or ""),
                    "options": list(q.get("options") or [])[:4],
                    "answer": int(q.get("answer") or 0),
                    "explanation": str(q.get("explanation") or ""),
                }
            )
    return {
        "title": title,
        "cards": cards,
        "questions": questions,
        "tips": tips,
        "sources": [],
    }


def export_trainer_json(
    db: Session,
    user: User,
    unit_id: uuid.UUID,
    *,
    include_progress: bool = True,
) -> tuple[dict, str]:
    unit = _get_unit_or_404(db, user, unit_id)
    if (unit.task_type or "") != "interactive":
        raise UnitError("Nur für interaktive Lerneinheiten", "invalid_task_type")
    if not unit.modules:
        raise UnitError("Keine Lernblöcke zum Exportieren", "thin_content")

    record = db.query(LearningRecord).filter(LearningRecord.unit_id == unit.id).first()
    modules = [_dec_module(m) for m in sorted(unit.modules, key=lambda x: x.order_index)]
    title = decrypt_text_master(unit.title_encrypted)
    brief = decrypt_text_master(unit.brief_encrypted) if unit.brief_encrypted else None
    recon = decrypt_json(record.reconstruction_encrypted) if record and record.reconstruction_encrypted else {}

    payload: dict = {
        "format": EXPORT_FORMAT,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "unit": {
            "title": title,
            "brief": brief,
            "subject": unit.subject,
            "language": unit.language,
            "target_age": unit.target_age,
            "difficulty": unit.difficulty,
            "task_type": unit.task_type,
            "trainer_options": get_trainer_options(recon if isinstance(recon, dict) else {}),
        },
        "modules": modules,
        "bio_ranger": _bio_ranger_block(modules, title=title),
    }
    if include_progress and record:
        profile_id = record.profile_id or unit.profile_id
        if profile_id:
            module_ids = [m.id for m in unit.modules]
            payload["progress"] = flashcard_progress_map(
                db, profile_id=profile_id, module_ids=module_ids
            )
    return payload, _slug_filename(title)


def _modules_from_payload(raw_modules: list) -> list[dict]:
    modules: list[dict] = []
    for index, raw in enumerate(raw_modules[:8]):
        if not isinstance(raw, dict):
            continue
        content = raw.get("content") if isinstance(raw.get("content"), dict) else {}
        quiz = raw.get("quiz") if isinstance(raw.get("quiz"), dict) else {"questions": []}
        modules.append(
            {
                "title": str(raw.get("title") or f"Bereich {index + 1}")[:200],
                "content": content,
                "quiz": quiz,
            }
        )
    if len(modules) < 1:
        raise UnitError("Import: keine Module gefunden", "bad_json")
    return modules


def _modules_from_bio_ranger(block: dict) -> list[dict]:
    cards_raw = block.get("cards") if isinstance(block.get("cards"), list) else []
    cards = []
    for item in cards_raw:
        if not isinstance(item, dict):
            continue
        cards.append(
            {
                "question": str(item.get("q") or item.get("question") or ""),
                "answer": str(item.get("a") or item.get("answer") or ""),
                "tip": str(item.get("tip") or ""),
            }
        )
    questions_raw = block.get("questions") if isinstance(block.get("questions"), list) else []
    questions = []
    for item in questions_raw:
        if not isinstance(item, dict):
            continue
        options = list(item.get("options") or [])[:4]
        if len(options) != 4:
            continue
        questions.append(
            {
                "q": str(item.get("q") or ""),
                "options": options,
                "answer": int(item.get("answer") or 0),
                "explanation": str(item.get("explanation") or ""),
            }
        )
    if not cards and not questions:
        raise UnitError("Import: Bio-Ranger-Block leer", "bad_json")
    return [
        {
            "title": str(block.get("title") or "Import")[:200],
            "content": {
                "intro": "",
                "knowledge": [],
                "cards": cards,
            },
            "quiz": {"questions": questions},
        }
    ]


def import_trainer_json(db: Session, user: User, payload: dict) -> dict:
    if not isinstance(payload, dict):
        raise UnitError("Ungültiges JSON", "bad_json")

    fmt = str(payload.get("format") or "").strip()
    unit_meta = payload.get("unit") if isinstance(payload.get("unit"), dict) else {}
    trainer_options = unit_meta.get("trainer_options") if isinstance(unit_meta.get("trainer_options"), dict) else None

    if fmt == EXPORT_FORMAT and isinstance(payload.get("modules"), list):
        modules = _modules_from_payload(payload["modules"])
        title = str(unit_meta.get("title") or "Import Trainer")[:200]
        brief = str(unit_meta.get("brief") or "") or None
        subject = unit_meta.get("subject")
        language = str(unit_meta.get("language") or "de")
        target_age = unit_meta.get("target_age")
        difficulty = int(unit_meta.get("difficulty") or 1)
    elif isinstance(payload.get("bio_ranger"), dict):
        block = payload["bio_ranger"]
        modules = _modules_from_bio_ranger(block)
        title = str(block.get("title") or payload.get("title") or "Import Trainer")[:200]
        brief = None
        subject = None
        language = "de"
        target_age = None
        difficulty = 1
    else:
        raise UnitError("Unbekanntes Import-Format (learnai-trainer-v1 oder bio_ranger)", "bad_json")

    validate_interactive_import(modules)

    result = create_unit(
        db,
        user,
        title=title,
        brief=brief,
        subject=subject,
        language=language,
        target_age=target_age,
        difficulty=min(max(difficulty, 1), 5),
        task_type="interactive",
    )
    new_unit = db.get(LearningUnit, uuid.UUID(result["id"]))
    if not new_unit:
        raise UnitError("Import fehlgeschlagen", "create_failed")

    for mod in list(new_unit.modules):
        db.delete(mod)
    db.flush()

    for index, raw in enumerate(modules):
        mod = UnitModule(
            unit=new_unit,
            order_index=index,
            title_encrypted=encrypt_text_master(raw["title"]),
            content_encrypted=encrypt_json(raw["content"]),
            quiz_encrypted=encrypt_json(shuffle_quiz_block(repair_quiz_block(raw["quiz"]))),
        )
        db.add(mod)

    new_unit.status = "ready"
    db.flush()

    record = db.query(LearningRecord).filter(LearningRecord.unit_id == new_unit.id).first()
    if record and trainer_options:
        recon = decrypt_json(record.reconstruction_encrypted) or {}
        if isinstance(recon, dict):
            from app.schemas import TrainerOptionsSchema

            recon["trainer_options"] = TrainerOptionsSchema.normalize_raw(trainer_options).model_dump()
            record.reconstruction_encrypted = encrypt_json(recon)

    db.flush()
    return _dec_unit(new_unit)
