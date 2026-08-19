"""Lerneinheit aus Quellen (Text/Fotos) in Lernblöcke + Quiz umwandeln."""

from __future__ import annotations

import uuid
from pathlib import Path

from sqlalchemy.orm import Session

from app.ai.errors import LlmError
from app.ai.providers import complete, describe_image, parse_json_object, resolve_provider
from app.config import settings
from app.core.crypto import decrypt_text_master, encrypt_text_master
from app.models import LearningRecord, LearningUnit, UnitModule, User
from app.services.crypto_json import encrypt_json
from app.services.user_service import get_user_settings
from app.services.unit_service import (
    _add_event,
    _dec_unit,
    _get_unit_or_404,
    maybe_auto_purge_after_extract,
    upload_dir,
)

TASK_HINTS = {
    "mixed": "Mischung aus kurzem Lerntext und Quizfragen.",
    "explain": "Schwerpunkt Erklären: ausführlicher Lerntext, nur 1–2 Kontrollfragen.",
    "quiz": "Schwerpunkt Quiz: kurze Einleitung, viele Verständnisfragen.",
    "vocab": "Sprachkurs/Vokabeln: Wort, Bedeutung, Beispielsatz, Mini-Quiz.",
    "practice": "Übungsaufgaben zum Selberlösen, danach Lösungshinweis im Quiz.",
    "exam": "Kurzprüfung: nur Aufgaben, knappe Anweisungen, klare richtige Antworten.",
}

SYSTEM = (
    "Du bist Lerncoach. Antworte immer mit einem JSON-Objekt, ohne Markdown."
    " Schema: {\"modules\":[{\"title\":\"...\",\"content\":{\"text\":\"...\"},"
    "\"quiz\":{\"questions\":[{\"q\":\"...\",\"options\":[\"A\",\"B\",\"C\",\"D\"],\"answer\":0}]}}]}"
    " 3 bis 6 Module, altersgerecht, Sprache wie vorgegeben. answer ist der Index der richtigen Option."
)


def generate_modules(
    db: Session,
    user: User,
    unit_id: uuid.UUID,
    *,
    provider: str | None = None,
) -> dict:
    unit = _get_unit_or_404(db, user, unit_id)
    prefs = get_user_settings(user)
    name = resolve_provider(provider or prefs.get("llm_provider") or None)
    model = (prefs.get("llm_model") or "").strip() or None
    notes = _collect_source_notes(db, unit, name)
    task = unit.task_type or "mixed"
    hint = TASK_HINTS.get(task, TASK_HINTS["mixed"])

    title = decrypt_text_master(unit.title_encrypted)
    brief = decrypt_text_master(unit.brief_encrypted) if unit.brief_encrypted else ""
    prompt = (
        f"Erstelle eine Lerneinheit.\n"
        f"Titel: {title}\n"
        f"Auftrag: {brief or '(kein Extra-Auftrag)'}\n"
        f"Fach: {unit.subject or 'offen'}\n"
        f"Sprache: {unit.language}\n"
        f"Zielalter: {unit.target_age or 'offen'}\n"
        f"Schwierigkeit 1-5: {unit.difficulty}\n"
        f"Aufgabentyp: {task} — {hint}\n\n"
        f"Material aus den Quellen:\n{notes or '(keine Quellen — nutze nur Titel und Auftrag)'}\n"
    )
    result = complete(prompt=prompt, provider=name, system=SYSTEM, model=model)
    try:
        parsed = parse_json_object(result["text"])
        modules = parsed.get("modules")
        if not isinstance(modules, list) or not modules:
            raise LlmError("Keine Module in der Antwort", "bad_json")
    except LlmError:
        modules = [
            {
                "title": "Lerntext",
                "content": {"text": result["text"]},
                "quiz": {"questions": []},
            }
        ]

    db.query(UnitModule).filter(UnitModule.unit_id == unit.id).delete()
    for index, raw in enumerate(modules[:8]):
        if not isinstance(raw, dict):
            continue
        mod_title = str(raw.get("title") or f"Block {index + 1}")[:200]
        content = raw.get("content") if isinstance(raw.get("content"), dict) else {"text": str(raw.get("content") or "")}
        quiz = raw.get("quiz") if isinstance(raw.get("quiz"), dict) else {"questions": []}
        db.add(
            UnitModule(
                unit_id=unit.id,
                order_index=index,
                title_encrypted=encrypt_text_master(mod_title),
                content_encrypted=encrypt_json(content),
                quiz_encrypted=encrypt_json(quiz),
            )
        )
    unit.status = "ready"
    db.flush()

    record = db.query(LearningRecord).filter(LearningRecord.unit_id == unit.id).first()
    if record:
        _add_event(
            db,
            record,
            "modules_generated",
            {"provider": result["provider"], "model": result["model"], "count": len(modules)},
        )
    return _dec_unit(unit)


def _collect_source_notes(db: Session, unit: LearningUnit, provider: str) -> str:
    parts: list[str] = []
    for source in unit.sources:
        label = (
            decrypt_text_master(source.original_name_encrypted)
            if source.original_name_encrypted
            else source.kind
        )
        if source.extracted_text_encrypted:
            parts.append(f"### {label}\n{decrypt_text_master(source.extracted_text_encrypted)}")
            continue
        if source.kind == "image" and source.storage_path and source.purged_at is None:
            path = Path(settings.upload_dir) / source.storage_path
            if not path.is_file():
                path = upload_dir() / source.storage_path
            if not path.is_file():
                continue
            data = path.read_bytes()
            if len(data) > 8 * 1024 * 1024:
                parts.append(f"### {label}\n(Bild zu groß für Vision, übersprungen)")
                continue
            mime = source.content_type or "image/jpeg"
            described = describe_image(
                image_bytes=data,
                mime=mime,
                prompt=(
                    "Das ist ein Foto aus einem Lernmittel. Extrahiere den sichtbaren Text "
                    "und beschreibe die Aufgabe so, dass man daraus eine Lerneinheit bauen kann. "
                    f"Sprache: {unit.language}."
                ),
                provider=provider,
            )
            source.extracted_text_encrypted = encrypt_text_master(described["text"])
            source.analysis_encrypted = encrypt_text_master(
                f"{described['provider']}:{described['model']}"
            )
            maybe_auto_purge_after_extract(db, unit, source)
            db.flush()
            parts.append(f"### {label}\n{described['text']}")
        elif source.kind == "document":
            parts.append(f"### {label}\n(Dokument — OCR folgt, Datei liegt vor)")
    return "\n\n".join(parts)
