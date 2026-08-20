"""Lerneinheit aus Quellen (Text/Fotos) in Lernblöcke + Quiz umwandeln."""

from __future__ import annotations

import logging
import time
import uuid
from pathlib import Path

from sqlalchemy.orm import Session

from app.ai.catalog import resolve_task_ai
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

from app.ai.task_types import AI_TASK_FOR_UNIT, hint_for_task

_log = logging.getLogger(__name__)

SYSTEM = (
    "Du bist Lerncoach. Antworte NUR mit einem JSON-Objekt, ohne Markdown-Umschlag.\n"
    'Schema: {"modules":[{"title":"...","content":{"text":"..."},'
    '"quiz":{"questions":[{"q":"...","options":["A","B","C","D"],"answer":0}]}}]}\n'
    "Regeln:\n"
    "- 4 bis 6 Module; jedes Modul = ein eigenes Teilthema mit Substanz (kein Ein-Satz-Block).\n"
    "- content.text: 120–350 Wörter, mehrere Absätze, Beispiele, altersgerecht und konkret.\n"
    "- quiz: pro Modul 3–5 Multiple-Choice-Fragen, je genau 4 Optionen; answer = 0-basierter Index.\n"
    "- Kein LaTeX mit Backslashes (statt \\(x\\) normale Schreibweise wie (x) oder x).\n"
    "- Sprache und Schwierigkeit wie vorgegeben."
)

_MIN_MODULES: dict[str, int] = {
    "explain": 3,
    "quiz": 4,
    "exam": 4,
    "review": 4,
    "vocab": 4,
}
_DEFAULT_MIN_MODULES = 4


def _word_count(text: str) -> int:
    return len([w for w in text.split() if w.strip()])


def _validate_modules(modules: list, *, task: str) -> None:
    min_modules = _MIN_MODULES.get(task, _DEFAULT_MIN_MODULES)
    if len(modules) < min_modules:
        raise LlmError(
            f"Zu wenige Module ({len(modules)}, mindestens {min_modules} erwartet)",
            "thin_content",
        )
    min_words = 80 if task in {"quiz", "exam", "review"} else 100
    min_questions = 4 if task in {"quiz", "exam", "review"} else 2 if task == "explain" else 3
    for index, raw in enumerate(modules[:8]):
        if not isinstance(raw, dict):
            raise LlmError(f"Modul {index + 1} hat ungültiges Format", "bad_json")
        content = raw.get("content")
        text = content.get("text", "") if isinstance(content, dict) else str(content or "")
        if _word_count(str(text)) < min_words:
            raise LlmError(
                f"Modul {index + 1} («{raw.get('title', '')}») ist zu kurz — mehr Erklärung nötig",
                "thin_content",
            )
        quiz = raw.get("quiz") if isinstance(raw.get("quiz"), dict) else {}
        questions = quiz.get("questions") if isinstance(quiz.get("questions"), list) else []
        if len(questions) < min_questions:
            raise LlmError(
                f"Modul {index + 1} hat zu wenige Quizfragen ({len(questions)}, mindestens {min_questions})",
                "thin_content",
            )
        for q_index, q in enumerate(questions):
            if not isinstance(q, dict):
                raise LlmError(f"Frage {q_index + 1} in Modul {index + 1} ungültig", "bad_json")
            options = q.get("options") if isinstance(q.get("options"), list) else []
            if len(options) < 4:
                raise LlmError(
                    f"Frage {q_index + 1} in Modul {index + 1} braucht 4 Antwortoptionen",
                    "bad_json",
                )


def generate_modules(
    db: Session,
    user: User,
    unit_id: uuid.UUID,
    *,
    provider: str | None = None,
) -> dict:
    unit = _get_unit_or_404(db, user, unit_id)
    from app.services.profile_service import resolve_prefs_for_profile

    prefs = resolve_prefs_for_profile(db, unit.profile_id) or get_user_settings(user)
    task = unit.task_type or "mixed"
    ai_task = AI_TASK_FOR_UNIT.get(task, "mixed")
    name, model = resolve_task_ai(prefs, ai_task, override=provider)
    name = resolve_provider(name)
    vision_name, vision_model = resolve_task_ai(prefs, "vision")
    _log.info(
        "generate_llm start unit_id=%s task=%s chat=%s/%s vision=%s/%s sources=%s profile_id=%s",
        unit_id,
        task,
        name,
        model or "(auto)",
        vision_name,
        vision_model or "(auto)",
        len(unit.sources or []),
        unit.profile_id,
    )
    t0 = time.monotonic()
    notes = _collect_source_notes(db, unit, prefs)
    _log.info(
        "generate_llm sources_done unit_id=%s duration_ms=%d notes_chars=%d",
        unit_id,
        int((time.monotonic() - t0) * 1000),
        len(notes),
    )
    hint = hint_for_task(task)
    recon = None
    from app.services.crypto_json import decrypt_json as _dj

    record = db.query(LearningRecord).filter(LearningRecord.unit_id == unit.id).first()
    if record and record.reconstruction_encrypted:
        recon = _dj(record.reconstruction_encrypted)
    math_focus = (recon or {}).get("math_focus") if isinstance(recon, dict) else None
    if math_focus:
        from app.ai.task_types import MATH_FOCUS_HINTS, MATH_FOCUS_OPTIONS

        label = next((o["label"] for o in MATH_FOCUS_OPTIONS if o["key"] == math_focus), math_focus)
        hint += f" Mathe-Schwerpunkt: {label}."

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
    _log.info(
        "generate_llm chat_start unit_id=%s provider=%s model=%s prompt_chars=%d",
        unit_id,
        name,
        model or "(auto)",
        len(prompt),
    )
    t_chat = time.monotonic()
    try:
        result = complete(prompt=prompt, provider=name, system=SYSTEM, model=model)
    except LlmError as exc:
        _log.warning(
            "generate_llm chat_fail unit_id=%s provider=%s model=%s code=%s duration_ms=%d msg=%s",
            unit_id,
            name,
            model or "(auto)",
            exc.code,
            int((time.monotonic() - t_chat) * 1000),
            exc.message,
        )
        raise
    _log.info(
        "generate_llm chat_ok unit_id=%s provider=%s model=%s response_chars=%d duration_ms=%d",
        unit_id,
        result.get("provider"),
        result.get("model"),
        len(result.get("text") or ""),
        int((time.monotonic() - t_chat) * 1000),
    )
    parsed = parse_json_object(result["text"])
    modules = parsed.get("modules")
    if not isinstance(modules, list) or not modules:
        raise LlmError("Keine Module in der KI-Antwort", "bad_json")
    _validate_modules(modules, task=task)

    for mod in list(unit.modules):
        db.delete(mod)
    db.flush()

    saved: list[UnitModule] = []
    for index, raw in enumerate(modules[:8]):
        if not isinstance(raw, dict):
            continue
        mod_title = str(raw.get("title") or f"Block {index + 1}")[:200]
        content = raw.get("content") if isinstance(raw.get("content"), dict) else {"text": str(raw.get("content") or "")}
        quiz = raw.get("quiz") if isinstance(raw.get("quiz"), dict) else {"questions": []}
        mod = UnitModule(
            unit=unit,
            order_index=index,
            title_encrypted=encrypt_text_master(mod_title),
            content_encrypted=encrypt_json(content),
            quiz_encrypted=encrypt_json(quiz),
        )
        db.add(mod)
        saved.append(mod)
    if not saved:
        raise LlmError("Keine verwertbaren Module in der KI-Antwort", "bad_json")

    unit.status = "ready"
    db.flush()

    record = db.query(LearningRecord).filter(LearningRecord.unit_id == unit.id).first()
    if record:
        _add_event(
            db,
            record,
            "modules_generated",
            {"provider": result["provider"], "model": result["model"], "count": len(saved)},
        )
    _log.info(
        "generate_llm done unit_id=%s modules=%d total_ms=%d",
        unit_id,
        len(saved),
        int((time.monotonic() - t0) * 1000),
    )
    return _dec_unit(unit)


def _collect_source_notes(db: Session, unit: LearningUnit, prefs: dict) -> str:
    from app.ai.extract import extract_pdf_text, fetch_url_text, transcribe_audio
    from app.ai.errors import LlmError

    parts: list[str] = []
    for source in unit.sources:
        label = (
            decrypt_text_master(source.original_name_encrypted)
            if source.original_name_encrypted
            else source.kind
        )
        if source.extracted_text_encrypted:
            text = decrypt_text_master(source.extracted_text_encrypted)
            parts.append(f"### {label}\n{text}")
            _log.info("generate_llm source_cached kind=%s label=%s chars=%d", source.kind, label, len(text))
            continue
        if source.kind == "url":
            try:
                text = fetch_url_text(label)
                source.extracted_text_encrypted = encrypt_text_master(text)
                db.flush()
                parts.append(f"### {label}\n{text}")
            except LlmError as exc:
                parts.append(f"### {label}\n(Link — {exc.message})")
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
            vision_name, vision_model = resolve_task_ai(prefs, "vision")
            _log.info(
                "generate_llm vision_start label=%s provider=%s model=%s bytes=%d",
                label,
                vision_name,
                vision_model or "(auto)",
                len(data),
            )
            t_vis = time.monotonic()
            try:
                described = describe_image(
                    image_bytes=data,
                    mime=mime,
                    prompt=(
                        "Das ist ein Foto aus einem Lernmittel. Extrahiere den sichtbaren Text "
                        "und beschreibe die Aufgabe so, dass man daraus eine Lerneinheit bauen kann. "
                        f"Sprache: {unit.language}."
                    ),
                    provider=vision_name,
                    model=vision_model,
                )
            except LlmError as exc:
                _log.warning(
                    "generate_llm vision_fail label=%s provider=%s model=%s code=%s duration_ms=%d msg=%s",
                    label,
                    vision_name,
                    vision_model or "(auto)",
                    exc.code,
                    int((time.monotonic() - t_vis) * 1000),
                    exc.message,
                )
                raise
            _log.info(
                "generate_llm vision_ok label=%s model=%s chars=%d duration_ms=%d",
                label,
                described.get("model"),
                len(described.get("text") or ""),
                int((time.monotonic() - t_vis) * 1000),
            )
            source.extracted_text_encrypted = encrypt_text_master(described["text"])
            source.analysis_encrypted = encrypt_text_master(
                f"{described['provider']}:{described['model']}"
            )
            maybe_auto_purge_after_extract(db, unit, source)
            db.flush()
            parts.append(f"### {label}\n{described['text']}")
        elif source.kind == "document" and source.storage_path and source.purged_at is None:
            path = Path(settings.upload_dir) / source.storage_path
            if not path.is_file():
                path = upload_dir() / source.storage_path
            if path.is_file():
                try:
                    text = extract_pdf_text(path)
                    source.extracted_text_encrypted = encrypt_text_master(text)
                    source.analysis_encrypted = encrypt_text_master("pypdf/vision")
                    maybe_auto_purge_after_extract(db, unit, source)
                    db.flush()
                    parts.append(f"### {label}\n{text}")
                except LlmError as exc:
                    parts.append(f"### {label}\n(PDF — {exc.message})")
            else:
                parts.append(f"### {label}\n(PDF-Datei nicht gefunden)")
        elif source.kind == "audio" and source.storage_path and source.purged_at is None:
            path = Path(settings.upload_dir) / source.storage_path
            if not path.is_file():
                path = upload_dir() / source.storage_path
            if path.is_file():
                try:
                    text = transcribe_audio(path, language=unit.language or "de")
                    source.extracted_text_encrypted = encrypt_text_master(text)
                    source.analysis_encrypted = encrypt_text_master("whisper-1")
                    maybe_auto_purge_after_extract(db, unit, source)
                    db.flush()
                    parts.append(f"### {label}\n{text}")
                except LlmError as exc:
                    parts.append(f"### {label}\n(Audio — {exc.message})")
            else:
                parts.append(f"### {label}\n(Audio-Datei nicht gefunden)")
    return "\n\n".join(parts)
