"""Tests für persistente Batch-Manifeste."""

from __future__ import annotations

from app.services.batch_import_registry import (
    build_batch_description,
    build_batch_label,
    list_batch_manifests,
    load_batch_manifest,
    manifest_summary,
    persist_batch_manifest,
)


def test_build_batch_label_with_posten_range():
    units = [
        {"title": "Posten 14", "posten": 14, "generate_status": "done"},
        {"title": "Posten 26", "posten": 26, "generate_status": "pending"},
    ]
    assert build_batch_label(subject="NMG Schweizer Geschichte", units=units) == (
        "NMG Schweizer Geschichte · Posten 14–26"
    )


def test_persist_and_list_batch_manifest(tmp_path, monkeypatch):
    monkeypatch.setattr("app.services.batch_import_registry._upload_root", lambda: tmp_path)
    job = {
        "batch_id": "11111111-1111-1111-1111-111111111111",
        "user_id": "22222222-2222-2222-2222-222222222222",
        "tenant_id": "33333333-3333-3333-3333-333333333333",
        "status": "done",
        "total": 1,
        "progress_pct": 100,
        "started_at": "2026-09-11T12:00:00+00:00",
        "updated_at": "2026-09-11T12:30:00+00:00",
        "pdf_path": str(tmp_path / "_batch" / "11111111-1111-1111-1111-111111111111" / "source.pdf"),
        "units": [{"title": "Posten 14", "posten": 14, "generate_status": "done", "unit_id": "abc"}],
        "payload": {"subject": "NMG", "default_preset": "posten_compact", "task_type": "interactive"},
    }
    persist_batch_manifest(job, source_filename="heft.pdf")
    loaded = load_batch_manifest("11111111-1111-1111-1111-111111111111")
    assert loaded
    assert loaded["label"] == "NMG · Posten 14"
    assert "heft.pdf" in str(loaded.get("description"))
    rows = list_batch_manifests(user_id="22222222-2222-2222-2222-222222222222")
    assert len(rows) == 1
    assert rows[0]["batch_id"] == job["batch_id"]
    assert manifest_summary(loaded)["unit_count_done"] == 1


def test_build_batch_description_counts_done():
    desc = build_batch_description(
        payload={"task_type": "interactive", "default_preset": "posten_compact"},
        units=[
            {"generate_status": "done"},
            {"generate_status": "failed"},
        ],
        source_filename="heft.pdf",
    )
    assert "1/2 fertig" in desc
    assert "interactive" in desc
