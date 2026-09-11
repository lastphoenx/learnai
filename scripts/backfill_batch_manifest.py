#!/usr/bin/env python3
"""Batch-Manifest auf Disk backfillen — Batch-Hub sichtbar auch ohne Redis.

Quellen (in Reihenfolge):
  1. Live-Redis / vorhandenes manifest.json
  2. Payload-JSON + DB-Lookup per Referenz-Code (Pilot NMG)

Beispiele:
  docker compose exec -T api python /opt/scripts/backfill_batch_manifest.py 3b6c2e13-7d59-4406-94f4-0dd5c2f97670
  docker compose exec -T api python /opt/scripts/backfill_batch_manifest.py 3b6c2e13-... --payload /opt/scripts/nmg_geschichte_batch_payload.example.json
  docker compose exec -T api python /opt/scripts/backfill_batch_manifest.py 3b6c2e13-... --dry-run
"""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

_backend = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(_backend if _backend.is_dir() else Path("/app")))

from app.core.db.session import SessionLocal  # noqa: E402
from app.models import LearningRecord, LearningUnit, User  # noqa: E402
from app.services.batch_import_registry import (  # noqa: E402
    batch_dir,
    load_batch_manifest,
    persist_batch_manifest,
    resolve_batch_job,
)
from app.services.crypto_json import decrypt_json  # noqa: E402

_DEFAULT_PAYLOAD = Path(__file__).resolve().parent / "nmg_geschichte_batch_payload.example.json"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _reference_code_for_posten(posten: int) -> str:
    return f"{posten + 2:04d}.0101"


def _review_reference_code() -> str:
    return "0029.0001"


def _unit_id_for_reference(db, tenant_id: uuid.UUID, ref_code: str) -> str | None:
    rows = (
        db.query(LearningUnit, LearningRecord)
        .join(LearningRecord, LearningRecord.unit_id == LearningUnit.id)
        .filter(LearningUnit.tenant_id == tenant_id)
        .all()
    )
    for unit, record in rows:
        recon = decrypt_json(record.reconstruction_encrypted) if record.reconstruction_encrypted else {}
        if not isinstance(recon, dict):
            continue
        code = str(recon.get("reference_code") or "").strip()
        if code == ref_code:
            return str(unit.id)
    return None


def _build_rows_from_payload(db, user: User, payload: dict) -> list[dict]:
    rows: list[dict] = []
    for spec in payload.get("units") or []:
        if not isinstance(spec, dict):
            continue
        posten = spec.get("posten")
        ref = _reference_code_for_posten(int(posten)) if posten not in (None, "") else None
        unit_id = _unit_id_for_reference(db, user.tenant_id, ref) if ref else None
        rows.append(
            {
                "title": spec.get("title"),
                "page_from": spec.get("page_from"),
                "page_to": spec.get("page_to"),
                "posten": posten,
                "preset": spec.get("preset"),
                "brief_suffix": spec.get("brief_suffix"),
                "generate_status": "done" if unit_id else "failed",
                "unit_id": unit_id,
                "error": None if unit_id else f"Keine Einheit mit Ref. {ref}",
                "reference_code": ref,
            }
        )
    review = payload.get("review_unit")
    if isinstance(review, dict):
        ref = _review_reference_code()
        unit_id = _unit_id_for_reference(db, user.tenant_id, ref)
        rows.append(
            {
                "title": review.get("title"),
                "page_from": review.get("page_from"),
                "page_to": review.get("page_to"),
                "posten": None,
                "preset": review.get("preset"),
                "brief_suffix": review.get("brief_suffix"),
                "generate_status": "done" if unit_id else "failed",
                "unit_id": unit_id,
                "error": None if unit_id else f"Keine Einheit mit Ref. {ref}",
                "is_review": True,
                "reference_code": ref,
            }
        )
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description="Batch-Manifest für Batch-Hub persistieren")
    parser.add_argument("batch_id", help="Batch-UUID")
    parser.add_argument(
        "--payload",
        default=str(_DEFAULT_PAYLOAD),
        help="Batch-Payload JSON (Default: NMG-Pilot)",
    )
    parser.add_argument("--user-id", help="Owner-UUID (Default: erster Admin)")
    parser.add_argument("--source-filename", default="NMG_Schweizer_Geschichte.pdf")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    batch_id = args.batch_id.strip()
    existing = load_batch_manifest(batch_id)
    live = resolve_batch_job(batch_id)
    if live and not args.dry_run:
        persist_batch_manifest(live, source_filename=args.source_filename)
        from app.services.batch_import_job import get_batch_import_job, update_batch_import_job

        if get_batch_import_job(batch_id):
            skip = frozenset({"batch_id", "from_manifest"})
            update_batch_import_job(batch_id, **{k: v for k, v in live.items() if k not in skip})
        manifest = load_batch_manifest(batch_id)
        print(f"OK: manifest aus {'Redis' if not live.get('from_manifest') else 'Archiv'} geschrieben")
        print(f"  label: {manifest.get('label') if manifest else '—'}")
        return 0
    if existing and not args.dry_run:
        print(f"OK: manifest existiert bereits — {existing.get('label')}")
        return 0

    payload_path = Path(args.payload)
    if not payload_path.is_file():
        print(f"Payload nicht gefunden: {payload_path}", file=sys.stderr)
        return 1
    payload = json.loads(payload_path.read_text(encoding="utf-8"))

    db = SessionLocal()
    try:
        user: User | None = None
        if args.user_id:
            user = db.query(User).filter(User.id == uuid.UUID(args.user_id)).first()
        if not user:
            user = db.query(User).filter(User.is_admin.is_(True)).order_by(User.created_at).first()
        if not user:
            print("Kein Benutzer gefunden", file=sys.stderr)
            return 1

        units = _build_rows_from_payload(db, user, payload)
        done = sum(1 for row in units if row.get("generate_status") == "done")
        pdf_path = batch_dir(batch_id) / "source.pdf"
        job = {
            "batch_id": batch_id,
            "user_id": str(user.id),
            "tenant_id": str(user.tenant_id),
            "status": "done" if done == len(units) else "partial",
            "cancel_requested": False,
            "total": len(units),
            "current_index": len(units) - 1,
            "progress_pct": int(100 * done / max(1, len(units))),
            "started_at": _now_iso(),
            "updated_at": _now_iso(),
            "pdf_path": str(pdf_path),
            "units": units,
            "payload": {
                "subject": payload.get("subject"),
                "math_focus": payload.get("math_focus"),
                "target_age": payload.get("target_age"),
                "language": payload.get("language") or "de",
                "difficulty": int(payload.get("difficulty") or 2),
                "task_type": payload.get("task_type") or "interactive",
                "default_preset": payload.get("default_preset"),
                "shared_brief_pages": payload.get("shared_brief_pages"),
                "shared_brief_text": payload.get("shared_brief_text"),
            },
            "source_filename": args.source_filename,
            "message": f"Backfill: {done}/{len(units)} Einheiten verknüpft",
            "error": None,
        }
        if args.dry_run:
            from app.services.batch_import_registry import build_batch_label, build_batch_description

            label = build_batch_label(subject=payload.get("subject"), units=units)
            desc = build_batch_description(
                payload=job["payload"],
                units=units,
                source_filename=args.source_filename,
            )
            print(f"dry-run batch_id={batch_id}")
            print(f"  label: {label}")
            print(f"  description: {desc}")
            print(f"  units: {done}/{len(units)} mit unit_id")
            for index, row in enumerate(units):
                print(
                    f"  {index + 1}. {row.get('title')} ref={row.get('reference_code')} "
                    f"unit_id={row.get('unit_id') or '—'}"
                )
            return 0 if done else 1

        persist_batch_manifest(job, source_filename=args.source_filename)
        manifest = load_batch_manifest(batch_id)
        print(f"OK: manifest geschrieben — {manifest.get('label') if manifest else batch_id}")
        print(f"  {done}/{len(units)} Posten verknüpft")
        return 0 if done else 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
