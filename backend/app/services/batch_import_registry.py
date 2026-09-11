"""Persistente Batch-Metadaten auf dem Dateisystem — überlebt Redis-TTL."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.config import settings


def _upload_root() -> Path:
    return Path(settings.upload_dir)


def batch_dir(batch_id: str) -> Path:
    return _upload_root() / "_batch" / batch_id


def manifest_path(batch_id: str) -> Path:
    return batch_dir(batch_id) / "manifest.json"


def manifest_path_for_job(job: dict[str, Any]) -> Path:
    pdf_path = str(job.get("pdf_path") or "").strip()
    if pdf_path:
        return Path(pdf_path).parent / "manifest.json"
    return manifest_path(batch_id_from_job(job))


def batch_id_from_job(job: dict[str, Any]) -> str:
    return str(job.get("batch_id") or "").strip()


def build_batch_label(
    *,
    subject: str | None,
    units: list[dict[str, Any]],
    source_filename: str | None = None,
) -> str:
    subject_part = (subject or "Batch-Import").strip() or "Batch-Import"
    postens = sorted(
        {
            int(row["posten"])
            for row in units
            if isinstance(row, dict) and row.get("posten") not in (None, "")
        }
    )
    if postens:
        if postens[0] == postens[-1]:
            range_part = f"Posten {postens[0]}"
        else:
            range_part = f"Posten {postens[0]}–{postens[-1]}"
    else:
        non_review = [row for row in units if isinstance(row, dict) and not row.get("is_review")]
        range_part = f"{len(non_review or units)} Einheiten"
    _ = source_filename
    return f"{subject_part} · {range_part}"


def build_batch_description(
    *,
    payload: dict[str, Any],
    units: list[dict[str, Any]],
    source_filename: str | None,
) -> str:
    parts: list[str] = []
    if source_filename:
        parts.append(f"PDF: {source_filename}")
    task_type = str(payload.get("task_type") or "").strip()
    if task_type:
        parts.append(task_type)
    preset = str(payload.get("default_preset") or "").strip()
    if preset:
        parts.append(f"Preset {preset}")
    done = sum(
        1
        for row in units
        if isinstance(row, dict) and row.get("generate_status") == "done"
    )
    parts.append(f"{done}/{len(units)} fertig")
    return " · ".join(parts)


def persist_batch_manifest(job: dict[str, Any], *, source_filename: str | None = None) -> None:
    batch_id = batch_id_from_job(job)
    if not batch_id:
        return
    payload = job.get("payload") if isinstance(job.get("payload"), dict) else {}
    units = job.get("units") if isinstance(job.get("units"), list) else []
    filename = source_filename or str(job.get("source_filename") or "").strip() or None
    manifest: dict[str, Any] = {
        "batch_id": batch_id,
        "user_id": job.get("user_id"),
        "tenant_id": job.get("tenant_id"),
        "label": build_batch_label(subject=payload.get("subject"), units=units, source_filename=filename),
        "description": build_batch_description(payload=payload, units=units, source_filename=filename),
        "source_filename": filename,
        "subject": payload.get("subject"),
        "status": job.get("status"),
        "cancel_requested": bool(job.get("cancel_requested")),
        "total": job.get("total"),
        "current_index": job.get("current_index"),
        "progress_pct": job.get("progress_pct"),
        "started_at": job.get("started_at"),
        "updated_at": job.get("updated_at"),
        "pdf_path": job.get("pdf_path"),
        "units": units,
        "payload": payload,
        "error": job.get("error"),
        "message": job.get("message"),
        "celery_task_id": job.get("celery_task_id"),
    }
    path = manifest_path_for_job(job)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")


def load_batch_manifest(batch_id: str) -> dict[str, Any] | None:
    path = manifest_path(batch_id)
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except (json.JSONDecodeError, OSError):
        return None


def manifest_summary(manifest: dict[str, Any]) -> dict[str, Any]:
    units = manifest.get("units") if isinstance(manifest.get("units"), list) else []
    return {
        "batch_id": manifest.get("batch_id"),
        "label": manifest.get("label"),
        "description": manifest.get("description"),
        "subject": manifest.get("subject"),
        "source_filename": manifest.get("source_filename"),
        "status": manifest.get("status"),
        "total": manifest.get("total"),
        "progress_pct": manifest.get("progress_pct"),
        "started_at": manifest.get("started_at"),
        "updated_at": manifest.get("updated_at"),
        "unit_count_done": sum(
            1
            for row in units
            if isinstance(row, dict) and row.get("generate_status") == "done"
        ),
    }


def list_batch_manifests(*, user_id: str, include_all: bool = False) -> list[dict[str, Any]]:
    root = _upload_root() / "_batch"
    if not root.is_dir():
        return []
    rows: list[dict[str, Any]] = []
    for child in root.iterdir():
        if not child.is_dir() or child.name.startswith("_"):
            continue
        manifest = load_batch_manifest(child.name)
        if not manifest:
            continue
        if not include_all and str(manifest.get("user_id")) != str(user_id):
            continue
        rows.append(manifest_summary(manifest))
    rows.sort(key=lambda row: str(row.get("updated_at") or ""), reverse=True)
    return rows


def resolve_batch_job(batch_id: str) -> dict[str, Any] | None:
    """Live-Job aus Redis, sonst Manifest vom Dateisystem."""
    from app.services.batch_import_job import get_batch_import_job

    live = get_batch_import_job(batch_id)
    if live:
        return live
    manifest = load_batch_manifest(batch_id)
    if manifest:
        return {**manifest, "from_manifest": True}
    return None
