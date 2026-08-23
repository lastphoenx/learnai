"""Golden-Set-Fixtures für die Pedagogy-Pipeline (Admin + Regression)."""

from __future__ import annotations

import json
import re
from pathlib import Path

from app.ai.source_pedagogy import build_pedagogy_digest, parse_pedagogy_extraction
from app.core.pedagogy_labels import is_schema_placeholder, material_labels_from_methods
from app.services.unit_service import upload_dir

_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,62}$", re.IGNORECASE)
_BUNDLED_DIR = Path(__file__).resolve().parent.parent / "fixtures" / "pedagogy_golden"


class PedagogyGoldenError(Exception):
    def __init__(self, message: str, code: str = "invalid"):
        super().__init__(message)
        self.message = message
        self.code = code


def _custom_dir_path() -> Path:
    return upload_dir() / "pedagogy_golden"


def _ensure_custom_dir() -> Path:
    path = _custom_dir_path()
    path.mkdir(parents=True, exist_ok=True)
    return path


def _normalize_name(name: str) -> str:
    stem = (name or "").strip().removesuffix(".json")
    if not _NAME_RE.match(stem):
        raise PedagogyGoldenError(
            "Ungültiger Name — nur Buchstaben, Zahlen, _ und - (max. 63 Zeichen)",
            "invalid_name",
        )
    return stem


def validate_pedagogy_fixture(
    payload: dict,
    *,
    min_method_labels: int = 2,
    fixture_name: str = "fixture",
) -> dict:
    summary, pedagogy = parse_pedagogy_extraction(json.dumps(payload))
    methods = pedagogy.get("methods") or []
    labels = material_labels_from_methods(methods)
    if len(labels) < min_method_labels:
        raise PedagogyGoldenError(
            f"{fixture_name}: mindestens {min_method_labels} Methoden-Labels erwartet, {len(labels)} gefunden",
            "validation_failed",
        )

    for method in methods:
        for field in ("when", "example", "label"):
            value = method.get(field) or ""
            if is_schema_placeholder(value):
                raise PedagogyGoldenError(
                    f"Schema-Platzhalter in methods.{field}: {value!r}",
                    "validation_failed",
                )

    patterns = pedagogy.get("exercise_patterns") or []
    if not patterns:
        raise PedagogyGoldenError(
            f"{fixture_name}: mindestens ein exercise_pattern erwartet",
            "validation_failed",
        )
    for pattern in patterns:
        if is_schema_placeholder(pattern):
            raise PedagogyGoldenError(
                f"Schema-Platzhalter in exercise_patterns: {pattern!r}",
                "validation_failed",
            )

    digest = build_pedagogy_digest(pedagogy)
    if "kurzer Satz" in digest or "kurzes Beispiel mit Zahlen" in digest:
        raise PedagogyGoldenError("Digest enthält Schema-Platzhalter", "validation_failed")
    if labels and labels[0] not in digest and labels[0][:20] not in digest:
        raise PedagogyGoldenError("Digest enthält kein erkanntes Methoden-Label", "validation_failed")

    if summary and is_schema_placeholder(summary):
        raise PedagogyGoldenError("Summary ist Schema-Platzhalter", "validation_failed")

    return {
        "ok": True,
        "method_count": len(methods),
        "label_count": len(labels),
        "pattern_count": len(patterns),
        "digest_preview": digest[:240],
        "summary": summary,
    }


def _fixture_meta(path: Path, *, editable: bool) -> dict:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {
            "name": path.stem,
            "editable": editable,
            "error": str(exc),
            "ok": False,
        }
    meta = payload.get("_meta") if isinstance(payload.get("_meta"), dict) else {}
    min_labels = int(meta.get("min_method_labels") or 2)
    body = {k: v for k, v in payload.items() if k != "_meta"}
    try:
        result = validate_pedagogy_fixture(body, min_method_labels=min_labels, fixture_name=path.stem)
        return {
            "name": path.stem,
            "editable": editable,
            "min_method_labels": min_labels,
            "subject_hint": meta.get("subject_hint"),
            "ok": True,
            **result,
        }
    except PedagogyGoldenError as exc:
        return {
            "name": path.stem,
            "editable": editable,
            "min_method_labels": min_labels,
            "ok": False,
            "error": exc.message,
        }


def list_pedagogy_golden_fixtures() -> list[dict]:
    items: dict[str, dict] = {}
    for directory, editable in ((_BUNDLED_DIR, False), (_custom_dir_path(), True)):
        if not directory.is_dir():
            continue
        for path in sorted(directory.glob("*.json")):
            items[path.stem] = _fixture_meta(path, editable=editable)
    return [items[key] for key in sorted(items)]


def get_pedagogy_golden_fixture(name: str) -> dict:
    stem = _normalize_name(name)
    custom = _custom_dir_path() / f"{stem}.json"
    bundled = _BUNDLED_DIR / f"{stem}.json"
    path = custom if custom.is_file() else bundled if bundled.is_file() else None
    if not path:
        raise PedagogyGoldenError("Fixture nicht gefunden", "not_found")
    payload = json.loads(path.read_text(encoding="utf-8"))
    meta = payload.get("_meta") if isinstance(payload.get("_meta"), dict) else {}
    content = {k: v for k, v in payload.items() if k != "_meta"}
    return {
        "name": stem,
        "editable": path.parent == _custom_dir_path(),
        "content": content,
        "min_method_labels": int(meta.get("min_method_labels") or 2),
        "subject_hint": meta.get("subject_hint"),
    }


def save_pedagogy_golden_fixture(
    name: str,
    content: dict,
    *,
    min_method_labels: int = 2,
    subject_hint: str | None = None,
) -> dict:
    stem = _normalize_name(name)
    if stem in {"README"}:
        raise PedagogyGoldenError("Dieser Name ist reserviert", "invalid_name")
    if min_method_labels < 1 or min_method_labels > 20:
        raise PedagogyGoldenError("min_method_labels muss 1–20 sein", "invalid")

    body = dict(content)
    body.pop("_meta", None)
    validate_pedagogy_fixture(body, min_method_labels=min_method_labels, fixture_name=stem)

    payload = dict(body)
    meta: dict = {"min_method_labels": min_method_labels}
    if subject_hint and subject_hint.strip():
        meta["subject_hint"] = subject_hint.strip()[:64]
    payload["_meta"] = meta

    path = _ensure_custom_dir() / f"{stem}.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return get_pedagogy_golden_fixture(stem)


def delete_pedagogy_golden_fixture(name: str) -> None:
    stem = _normalize_name(name)
    path = _custom_dir_path() / f"{stem}.json"
    if not path.is_file():
        raise PedagogyGoldenError("Nur benutzerdefinierte Fixtures können gelöscht werden", "not_found")
    path.unlink()


def run_pedagogy_golden_suite() -> dict:
    fixtures = list_pedagogy_golden_fixtures()
    passed = sum(1 for row in fixtures if row.get("ok"))
    return {
        "total": len(fixtures),
        "passed": passed,
        "failed": len(fixtures) - passed,
        "fixtures": fixtures,
    }
