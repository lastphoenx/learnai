"""PDF-Batch-Import: mehrere Lerneinheiten aus Seitenbereichen."""

from __future__ import annotations

import json
import logging
import uuid
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.ai.errors import LlmError
from app.ai.extract import extract_pdf_pages_text, pdf_page_count, render_pdf_pages
from app.core.trainer_presets import DEFAULT_BATCH_PRESET_ID, DEFAULT_PRESET_ID
from app.models import User
from app.services.batch_import_job import (
    batch_cancel_requested,
    batch_can_resume,
    batch_is_active,
    create_batch_import_job,
    get_batch_import_job,
    new_batch_id,
    request_batch_cancel,
    set_batch_unit_row,
    update_batch_import_job,
)
from app.services.generate_limits import acquire_batch_generate_rate_slot
from app.services.unit_service import UnitError, add_source, create_unit, upload_dir

_log = logging.getLogger(__name__)

MAX_BATCH_UNITS = 30


def _parse_payload(raw: str | dict) -> dict[str, Any]:
    if isinstance(raw, dict):
        data = raw
    else:
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise UnitError("Ungültiges JSON im Batch-Auftrag", "invalid_batch_payload") from exc
    if not isinstance(data, dict):
        raise UnitError("Batch-Auftrag muss ein JSON-Objekt sein", "invalid_batch_payload")
    return data


def _unit_specs(payload: dict[str, Any]) -> list[dict[str, Any]]:
    units = payload.get("units")
    if not isinstance(units, list) or not units:
        raise UnitError("Mindestens eine Lerneinheit im Batch nötig", "invalid_batch_payload")
    if len(units) > MAX_BATCH_UNITS:
        raise UnitError(f"Maximal {MAX_BATCH_UNITS} Lerneinheiten pro Batch", "invalid_batch_payload")
    out: list[dict[str, Any]] = []
    for i, row in enumerate(units):
        if not isinstance(row, dict):
            raise UnitError(f"Einheit {i + 1}: ungültiges Objekt", "invalid_batch_payload")
        title = str(row.get("title") or "").strip()
        if not title:
            raise UnitError(f"Einheit {i + 1}: Titel fehlt", "invalid_batch_payload")
        try:
            page_from = int(row["page_from"])
            page_to = int(row["page_to"])
        except (KeyError, TypeError, ValueError) as exc:
            raise UnitError(f"Einheit {i + 1}: page_from/page_to fehlen", "invalid_batch_payload") from exc
        posten_raw = row.get("posten")
        posten = int(posten_raw) if posten_raw not in (None, "") else None
        out.append(
            {
                "title": title,
                "page_from": page_from,
                "page_to": page_to,
                "posten": posten,
                "preset": (str(row.get("preset") or "").strip() or None),
                "brief_suffix": (str(row.get("brief_suffix") or "").strip() or None),
            }
        )
    return out


def _review_spec(payload: dict[str, Any]) -> dict[str, Any] | None:
    raw = payload.get("review_unit")
    if not raw:
        return None
    if not isinstance(raw, dict):
        raise UnitError("review_unit muss ein Objekt sein", "invalid_batch_payload")
    title = str(raw.get("title") or "").strip()
    if not title:
        raise UnitError("review_unit: Titel fehlt", "invalid_batch_payload")
    try:
        page_from = int(raw["page_from"])
        page_to = int(raw["page_to"])
    except (KeyError, TypeError, ValueError) as exc:
        raise UnitError("review_unit: page_from/page_to fehlen", "invalid_batch_payload") from exc
    return {
        "title": title,
        "page_from": page_from,
        "page_to": page_to,
        "preset": (str(raw.get("preset") or "exam_review").strip() or "exam_review"),
        "brief_suffix": (str(raw.get("brief_suffix") or "").strip() or None),
        "posten": None,
        "is_review": True,
    }


def _validate_page_ranges(pdf_path: Path, specs: list[dict[str, Any]]) -> None:
    count = pdf_page_count(pdf_path)
    for i, spec in enumerate(specs):
        start = int(spec["page_from"])
        end = int(spec["page_to"])
        if start < 1 or end < 1 or start > end:
            raise UnitError(f"Einheit {i + 1}: ungültiger Seitenbereich", "invalid_page_range")
        if start > count or end > count:
            raise UnitError(
                f"Einheit {i + 1}: Seiten {start}–{end} ausserhalb PDF (1–{count})",
                "invalid_page_range",
            )


def _intro_page_ranges(payload: dict[str, Any]) -> list[tuple[int, int]]:
    pages = payload.get("shared_brief_pages")
    if not isinstance(pages, list) or not pages:
        return []
    nums = sorted({int(p) for p in pages if int(p) > 0})
    if not nums:
        return []
    ranges: list[tuple[int, int]] = []
    start = end = nums[0]
    for page in nums[1:]:
        if page == end + 1:
            end = page
            continue
        ranges.append((start, end))
        start = end = page
    ranges.append((start, end))
    return ranges


def _validate_intro_pages(pdf_path: Path, payload: dict[str, Any]) -> None:
    count = pdf_page_count(pdf_path)
    for start, end in _intro_page_ranges(payload):
        if start < 1 or end < 1 or start > end:
            raise UnitError("Intro-Seiten: ungültiger Bereich", "invalid_page_range")
        if start > count or end > count:
            raise UnitError(
                f"Intro-Seiten {start}–{end} ausserhalb PDF (1–{count})",
                "invalid_page_range",
            )


def _batch_storage_dir(batch_id: str) -> Path:
    path = upload_dir() / "_batch" / batch_id
    path.mkdir(parents=True, exist_ok=True)
    return path


def _build_shared_brief(pdf_path: Path, payload: dict[str, Any]) -> str:
    override = str(payload.get("shared_brief_text") or "").strip()
    if override:
        return override
    ranges = _intro_page_ranges(payload)
    if not ranges:
        return ""
    text_parts: list[str] = []
    for page_from, page_to in ranges:
        chunk = extract_pdf_pages_text(
            pdf_path,
            page_from=page_from,
            page_to=page_to,
            vision_fallback=False,
        )
        if chunk.strip():
            text_parts.append(chunk.strip())
    return "\n\n".join(text_parts).strip()


def _compose_brief(*, shared: str, suffix: str | None, title: str) -> str | None:
    parts = [p for p in (shared.strip() if shared else "", (suffix or "").strip()) if p]
    if not parts:
        return f"Lerneinheit: {title}. Nur Stoff der zugehörigen Heftseiten."
    return "\n\n".join(parts)


def _attach_pdf_pages(
    db: Session,
    user: User,
    unit_id: uuid.UUID,
    pdf_path: Path,
    *,
    page_from: int,
    page_to: int,
) -> None:
    for page_num, png_bytes in render_pdf_pages(pdf_path, page_from=page_from, page_to=page_to):
        add_source(
            db,
            user,
            unit_id,
            filename=f"heft-seite-{page_num:02d}.png",
            content_type="image/png",
            data=png_bytes,
        )


def _profile_ids_from_payload(db: Session, user: User, payload: dict[str, Any]) -> list[uuid.UUID | None]:
    from app.services.unit_service import _resolve_profile_targets

    profile_ids_raw = payload.get("profile_ids")
    profile_id_raw = payload.get("profile_id")
    try:
        profile_ids = [uuid.UUID(x) for x in profile_ids_raw] if profile_ids_raw else None
        profile_id = uuid.UUID(profile_id_raw) if profile_id_raw else None
    except ValueError as exc:
        raise UnitError("Ungültige Profil-ID", "invalid_profile") from exc
    return _resolve_profile_targets(db, user, profile_id=profile_id, profile_ids=profile_ids)


def start_batch_import(
    db: Session,
    user: User,
    *,
    pdf_bytes: bytes,
    filename: str,
    payload_raw: str | dict,
) -> dict[str, Any]:
    from app.core.upload_validation import UploadValidationError, validate_upload_bytes

    payload = _parse_payload(payload_raw)
    specs = _unit_specs(payload)
    review = _review_spec(payload)
    all_specs = list(specs)
    if review:
        all_specs.append(review)

    try:
        detected = validate_upload_bytes(pdf_bytes, filename=filename or "batch.pdf", allow_audio=False)
    except UploadValidationError as exc:
        raise UnitError(str(exc), exc.code) from exc
    if detected.kind != "document":
        raise UnitError("Batch-Import benötigt eine PDF-Datei", "invalid_file_type")

    batch_id = new_batch_id()
    storage = _batch_storage_dir(batch_id)
    pdf_path = storage / "source.pdf"
    pdf_path.write_bytes(pdf_bytes)

    _validate_page_ranges(pdf_path, all_specs)
    _validate_intro_pages(pdf_path, payload)
    acquire_batch_generate_rate_slot(user_id=str(user.id))

    unit_rows: list[dict[str, Any]] = []
    for spec in specs:
        unit_rows.append(
            {
                "title": spec["title"],
                "page_from": spec["page_from"],
                "page_to": spec["page_to"],
                "posten": spec.get("posten"),
                "preset": spec.get("preset"),
                "brief_suffix": spec.get("brief_suffix"),
                "generate_status": "pending",
                "unit_id": None,
                "error": None,
            }
        )
    if review:
        unit_rows.append(
            {
                "title": review["title"],
                "page_from": review["page_from"],
                "page_to": review["page_to"],
                "posten": None,
                "preset": review.get("preset"),
                "brief_suffix": review.get("brief_suffix"),
                "generate_status": "pending",
                "unit_id": None,
                "error": None,
                "is_review": True,
            }
        )

    job = create_batch_import_job(
        batch_id=batch_id,
        user_id=str(user.id),
        tenant_id=str(user.tenant_id),
        total=len(unit_rows),
        pdf_path=str(pdf_path),
        units=unit_rows,
    )
    job["payload"] = {
        "subject": payload.get("subject"),
        "math_focus": payload.get("math_focus"),
        "target_age": payload.get("target_age"),
        "language": payload.get("language") or "de",
        "difficulty": int(payload.get("difficulty") or 1),
        "task_type": (str(payload.get("task_type") or "interactive").strip().lower()),
        "default_preset": (str(payload.get("default_preset") or DEFAULT_BATCH_PRESET_ID).strip()),
        "shared_brief_pages": payload.get("shared_brief_pages"),
        "shared_brief_text": payload.get("shared_brief_text"),
        "profile_id": payload.get("profile_id"),
        "profile_ids": payload.get("profile_ids"),
    }
    update_batch_import_job(batch_id, payload=job["payload"])

    from app.tasks.batch_import import batch_import_task

    task = batch_import_task.delay(batch_id, str(user.id))
    update_batch_import_job(batch_id, celery_task_id=task.id)

    return {
        "batch_job_id": batch_id,
        "unit_count": len(unit_rows),
        "status_url": f"/api/v1/units/batch-import/{batch_id}",
        "job": get_batch_import_job(batch_id),
    }


def get_batch_import_status(db: Session, user: User, batch_id: str) -> dict[str, Any]:
    job = get_batch_import_job(batch_id)
    if not job:
        raise UnitError("Batch-Job nicht gefunden", "not_found")
    if str(job.get("user_id")) != str(user.id) and not user.is_admin:
        raise UnitError("Kein Zugriff auf diesen Batch-Job", "forbidden")
    return job


def cancel_batch_import(db: Session, user: User, batch_id: str) -> dict[str, Any]:
    job = get_batch_import_status(db, user, batch_id)
    if not batch_is_active(job):
        return job
    updated = request_batch_cancel(batch_id)
    if not updated:
        raise UnitError("Batch-Job nicht gefunden", "not_found")
    return updated


def resume_batch_import(db: Session, user: User, batch_id: str) -> dict[str, Any]:
    """Fehlgeschlagene/abgebrochene Batch-Jobs fortsetzen — fertige Einheiten werden übersprungen."""
    job = get_batch_import_status(db, user, batch_id)
    if batch_is_active(job):
        raise UnitError("Batch läuft bereits", "conflict")
    if not batch_can_resume(job):
        raise UnitError("Batch kann nicht fortgesetzt werden", "invalid_state")

    pdf_path = Path(str(job.get("pdf_path") or ""))
    if not pdf_path.is_file():
        raise UnitError("PDF-Datei nicht mehr vorhanden — neuer Batch nötig", "not_found")

    updated_units: list[dict[str, Any]] = []
    for row in job.get("units") or []:
        if not isinstance(row, dict):
            updated_units.append(row)
            continue
        next_row = dict(row)
        if next_row.get("generate_status") == "done":
            updated_units.append(next_row)
            continue
        next_row["generate_status"] = "pending"
        next_row["error"] = None
        next_row["unit_id"] = None
        updated_units.append(next_row)

    update_batch_import_job(
        batch_id,
        status="queued",
        cancel_requested=False,
        error=None,
        message="Fortsetzung in Warteschlange…",
        units=updated_units,
    )

    from app.tasks.batch_import import batch_import_task

    task = batch_import_task.delay(batch_id, str(user.id))
    update_batch_import_job(batch_id, celery_task_id=task.id)
    resumed = get_batch_import_job(batch_id)
    if not resumed:
        raise UnitError("Batch-Job nicht gefunden", "not_found")
    return resumed


def _spec_from_job_row(row: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "title": row["title"],
        "page_from": row["page_from"],
        "page_to": row["page_to"],
        "posten": row.get("posten"),
        "preset": row.get("preset") or payload.get("default_preset") or DEFAULT_BATCH_PRESET_ID,
        "brief_suffix": row.get("brief_suffix"),
    }


def _fail_batch_job(batch_id: str, message: str) -> None:
    update_batch_import_job(
        batch_id,
        status="failed",
        error=message,
        message=message,
    )


def run_batch_import(batch_id: str, user_id: str) -> None:
    """Celery-Einstieg: Einheiten anlegen, Quellen rendern, nacheinander generieren."""
    from app.core.db.session import SessionLocal
    from app.services.batch_import_runner import process_batch_import_unit

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == uuid.UUID(user_id)).first()
        job = get_batch_import_job(batch_id)
        if not user or not job:
            return

        pdf_path = Path(str(job.get("pdf_path") or ""))
        if not pdf_path.is_file():
            update_batch_import_job(
                batch_id,
                status="failed",
                error="PDF-Datei nicht gefunden",
                message="PDF-Datei nicht gefunden",
            )
            return

        payload = job.get("payload") if isinstance(job.get("payload"), dict) else {}
        try:
            update_batch_import_job(batch_id, status="running", message="Batch-Import läuft…")
            shared_brief = _build_shared_brief(pdf_path, payload)
            targets = _profile_ids_from_payload(db, user, payload)
            profile_id = targets[0] if targets else None
        except UnitError as exc:
            _fail_batch_job(batch_id, exc.message)
            return
        except Exception:
            _log.exception("batch_import setup failed batch=%s", batch_id)
            _fail_batch_job(batch_id, "Batch-Import fehlgeschlagen")
            return

        units = job.get("units") or []
        failures = 0
        for index, row in enumerate(units):
            if batch_cancel_requested(batch_id):
                update_batch_import_job(
                    batch_id,
                    status="cancelled",
                    message="Batch abgebrochen",
                )
                break
            if not isinstance(row, dict):
                continue
            if row.get("generate_status") == "done":
                continue
            set_batch_unit_row(batch_id, index, generate_status="running")
            spec = _spec_from_job_row(row, payload)
            try:
                unit_id = process_batch_import_unit(
                    db,
                    user,
                    pdf_path=pdf_path,
                    shared_brief=shared_brief,
                    spec=spec,
                    profile_id=profile_id,
                    payload=payload,
                )
                db.commit()
                set_batch_unit_row(
                    batch_id,
                    index,
                    unit_id=str(unit_id),
                    generate_status="done",
                    error=None,
                )
            except (UnitError, LlmError) as exc:
                db.rollback()
                failures += 1
                msg = getattr(exc, "message", str(exc))
                set_batch_unit_row(
                    batch_id,
                    index,
                    generate_status="failed",
                    error=msg,
                )
                _log.warning("batch_import unit failed batch=%s index=%s msg=%s", batch_id, index, msg)
            except Exception:
                db.rollback()
                failures += 1
                set_batch_unit_row(
                    batch_id,
                    index,
                    generate_status="failed",
                    error="Generierung fehlgeschlagen",
                )
                _log.exception("batch_import unit failed batch=%s index=%s", batch_id, index)

        if batch_cancel_requested(batch_id) or (get_batch_import_job(batch_id) or {}).get("cancel_requested"):
            update_batch_import_job(
                batch_id,
                status="cancelled",
                message="Batch abgebrochen",
            )
            return
        if failures and failures < len(units):
            update_batch_import_job(
                batch_id,
                status="partial",
                message=f"Teilweise fertig ({failures} Fehler)",
            )
        elif failures:
            update_batch_import_job(
                batch_id,
                status="failed",
                error="Alle Einheiten fehlgeschlagen",
                message="Batch fehlgeschlagen",
            )
        else:
            update_batch_import_job(
                batch_id,
                status="done",
                message="Batch-Import abgeschlossen",
                progress_pct=100,
            )
    finally:
        db.close()
