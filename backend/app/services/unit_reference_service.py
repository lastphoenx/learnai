"""Lesbare Referenz-Codes für Lerneinheiten (Familie + Instanz)."""

from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models import LearningRecord, LearningUnit
from app.services.crypto_json import decrypt_json, encrypt_json

_AWARE_MIN = datetime.min.replace(tzinfo=timezone.utc)


def _created_sort_key(value: object | None) -> datetime:
    if isinstance(value, datetime):
        return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)
    return _AWARE_MIN


_REF_RE = re.compile(r"^(\d{4})(?:\.(\d{4}))?$")


class UnitReferenceError(Exception):
    def __init__(self, message: str, code: str = "invalid"):
        super().__init__(message)
        self.message = message
        self.code = code


def parse_reference_code(ref: str) -> tuple[str, str | None]:
    """'0001' -> ('0001', None); '0001.0002' -> ('0001', '0002')."""
    cleaned = (ref or "").strip()
    match = _REF_RE.match(cleaned)
    if not match:
        raise UnitReferenceError(
            "Ungültige Referenz — Format: 0001 (Familie) oder 0001.0001 (Instanz)",
            "invalid",
        )
    family = match.group(1)
    instance = match.group(2)
    return family, instance


def reference_codes_from_recon(recon: dict | None) -> tuple[str | None, str | None, str | None]:
    if not isinstance(recon, dict):
        return None, None, None
    family = str(recon.get("reference_family") or "").strip() or None
    instance = str(recon.get("reference_instance") or "").strip() or None
    code = str(recon.get("reference_code") or "").strip() or None
    if not code and family and instance:
        code = f"{family}.{instance}"
    return family, instance, code


def _template_root_for_unit(unit: LearningUnit, recon: dict | None) -> uuid.UUID:
    if isinstance(recon, dict):
        root = str(recon.get("template_root_id") or "").strip()
        if root:
            try:
                return uuid.UUID(root)
            except ValueError:
                pass
    return unit.id


def _family_groups(db: Session, tenant_id: uuid.UUID) -> dict[uuid.UUID, list[tuple[LearningUnit, LearningRecord]]]:
    """template_root_id -> [(unit, record), ...] sortiert nach created_at."""
    groups: dict[uuid.UUID, list[tuple[LearningUnit, LearningRecord, object]]] = {}
    rows = (
        db.query(LearningUnit, LearningRecord)
        .join(LearningRecord, LearningRecord.unit_id == LearningUnit.id)
        .filter(LearningUnit.tenant_id == tenant_id)
        .all()
    )
    for unit, record in rows:
        recon = decrypt_json(record.reconstruction_encrypted) if record.reconstruction_encrypted else {}
        if not isinstance(recon, dict):
            recon = {}
        root_id = _template_root_for_unit(unit, recon)
        groups.setdefault(root_id, []).append((unit, record, unit.created_at))
    return {
        root_id: [
            (unit, record)
            for unit, record, _ in sorted(items, key=lambda row: _created_sort_key(row[2]))
        ]
        for root_id, items in groups.items()
    }


def _family_order_from_groups(
    groups: dict[uuid.UUID, list[tuple[LearningUnit, LearningRecord]]],
) -> dict[uuid.UUID, str]:
    ordered_roots = sorted(
        groups.items(),
        key=lambda item: _created_sort_key(item[1][0][0].created_at if item[1] else None),
    )
    return {root_id: f"{index:04d}" for index, (root_id, _) in enumerate(ordered_roots, start=1)}


def _family_order(db: Session, tenant_id: uuid.UUID) -> dict[uuid.UUID, str]:
    return _family_order_from_groups(_family_groups(db, tenant_id))


def _compute_codes_for_unit(
    db: Session,
    tenant_id: uuid.UUID,
    unit: LearningUnit,
    record: LearningRecord,
) -> tuple[str, str, str]:
    recon = decrypt_json(record.reconstruction_encrypted) if record.reconstruction_encrypted else {}
    if not isinstance(recon, dict):
        recon = {}
    root_id = _template_root_for_unit(unit, recon)
    groups = _family_groups(db, tenant_id)
    family_map = _family_order_from_groups(groups)
    family = family_map.get(root_id) or f"{len(family_map) + 1:04d}"

    siblings = groups.get(root_id, [])
    instance = "0001"
    for index, (sibling_unit, _record) in enumerate(siblings, start=1):
        if sibling_unit.id == unit.id:
            instance = f"{index:04d}"
            break

    code = f"{family}.{instance}"
    return family, instance, code


def ensure_unit_reference_codes(
    db: Session,
    unit: LearningUnit,
    record: LearningRecord | None,
    *,
    persist: bool = True,
) -> dict[str, str | None]:
    if not record:
        return {"reference_family": None, "reference_instance": None, "reference_code": None}

    recon = decrypt_json(record.reconstruction_encrypted) if record.reconstruction_encrypted else {}
    if not isinstance(recon, dict):
        recon = {}

    family, instance, code = reference_codes_from_recon(recon)
    if code:
        return {
            "reference_family": family,
            "reference_instance": instance,
            "reference_code": code,
        }

    family, instance, code = _compute_codes_for_unit(db, unit.tenant_id, unit, record)
    if persist:
        recon["reference_family"] = family
        recon["reference_instance"] = instance
        recon["reference_code"] = code
        if not recon.get("template_root_id"):
            recon["template_root_id"] = str(unit.id)
        record.reconstruction_encrypted = encrypt_json(recon)
        db.flush()

    return {
        "reference_family": family,
        "reference_instance": instance,
        "reference_code": code,
    }


def attach_reference_fields(row: dict, refs: dict[str, str | None]) -> None:
    row["reference_family"] = refs.get("reference_family")
    row["reference_instance"] = refs.get("reference_instance")
    row["reference_code"] = refs.get("reference_code")


def find_units_by_reference(
    db: Session,
    tenant_id: uuid.UUID,
    ref: str,
) -> tuple[str, str | None, list[tuple[LearningUnit, LearningRecord]]]:
    family, instance = parse_reference_code(ref)
    matches: list[tuple[LearningUnit, LearningRecord]] = []

    groups = _family_groups(db, tenant_id)
    family_map = _family_order(db, tenant_id)
    root_ids = [root for root, code in family_map.items() if code == family]
    if not root_ids:
        raise UnitReferenceError(f"Keine Lerneinheit mit Familien-Referenz {family}", "not_found")

    for root_id in root_ids:
        for unit, record in groups.get(root_id, []):
            refs = ensure_unit_reference_codes(db, unit, record, persist=True)
            if refs.get("reference_family") != family:
                continue
            if instance is None:
                matches.append((unit, record))
            elif refs.get("reference_instance") == instance:
                matches.append((unit, record))

    if not matches:
        label = f"{family}.{instance}" if instance else family
        raise UnitReferenceError(f"Keine Lerneinheit für Referenz {label}", "not_found")

    matches.sort(key=lambda pair: pair[0].created_at or pair[0].updated_at)
    return family, instance, matches
