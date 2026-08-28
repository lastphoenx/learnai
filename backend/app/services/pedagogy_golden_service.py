"""Golden-Set-Fixtures für die Pedagogy-Pipeline (Repo-only, Admin read-only)."""

from __future__ import annotations

import json
from pathlib import Path

from app.ai.source_pedagogy import build_pedagogy_digest, parse_pedagogy_extraction
from app.ai.subject_focus import SUBJECT_FOCUS_GROUPS
from app.core.pedagogy_labels import is_schema_placeholder, material_labels_from_methods

_BUNDLED_DIR = Path(__file__).resolve().parent.parent / "fixtures" / "pedagogy_golden"
_SUBJECT_GROUP_LABELS = {str(g["id"]): str(g["label"]) for g in SUBJECT_FOCUS_GROUPS}
_EXPECTED_SUBJECT_GROUPS = [str(g["id"]) for g in SUBJECT_FOCUS_GROUPS]


class PedagogyGoldenError(Exception):
    def __init__(self, message: str, code: str = "invalid"):
        super().__init__(message)
        self.message = message
        self.code = code


def expected_subject_groups() -> list[dict]:
    return [
        {"id": gid, "label": _SUBJECT_GROUP_LABELS[gid]}
        for gid in _EXPECTED_SUBJECT_GROUPS
    ]


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


def _read_fixture_meta(path: Path) -> dict:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {
            "name": path.stem,
            "file": path.name,
            "error": str(exc),
            "ok": False,
        }

    meta = payload.get("_meta") if isinstance(payload.get("_meta"), dict) else {}
    min_labels = int(meta.get("min_method_labels") or 2)
    subject_group = str(meta.get("subject_group") or "").strip() or None
    subject_hint = str(meta.get("subject_hint") or "").strip() or None
    body = {k: v for k, v in payload.items() if k != "_meta"}

    row: dict = {
        "name": path.stem,
        "file": path.name,
        "min_method_labels": min_labels,
        "subject_group": subject_group,
        "subject_group_label": _SUBJECT_GROUP_LABELS.get(subject_group or "", subject_group),
        "subject_hint": subject_hint,
    }

    if subject_group and subject_group not in _EXPECTED_SUBJECT_GROUPS:
        row["ok"] = False
        row["error"] = f"Unbekannte subject_group {subject_group!r} — erlaubt: {', '.join(_EXPECTED_SUBJECT_GROUPS)}"
        return row

    try:
        result = validate_pedagogy_fixture(body, min_method_labels=min_labels, fixture_name=path.stem)
        row["ok"] = True
        row.update(result)
    except PedagogyGoldenError as exc:
        row["ok"] = False
        row["error"] = exc.message

    if not subject_group:
        row["ok"] = False
        row["error"] = (row.get("error") + " · " if row.get("error") else "") + (
            "_meta.subject_group fehlt (math, language, nmg, german, nature)"
        )

    return row


def list_pedagogy_golden_fixtures() -> list[dict]:
    if not _BUNDLED_DIR.is_dir():
        return []
    return [_read_fixture_meta(path) for path in sorted(_BUNDLED_DIR.glob("*.json"))]


def pedagogy_golden_coverage(fixtures: list[dict] | None = None) -> dict:
    rows = fixtures if fixtures is not None else list_pedagogy_golden_fixtures()
    by_group: dict[str, list[str]] = {gid: [] for gid in _EXPECTED_SUBJECT_GROUPS}
    for row in rows:
        group = row.get("subject_group")
        if group in by_group:
            by_group[group].append(row["name"])

    covered = [
        {
            "id": gid,
            "label": _SUBJECT_GROUP_LABELS[gid],
            "fixtures": by_group[gid],
        }
        for gid in _EXPECTED_SUBJECT_GROUPS
        if by_group[gid]
    ]
    missing = [
        {"id": gid, "label": _SUBJECT_GROUP_LABELS[gid]}
        for gid in _EXPECTED_SUBJECT_GROUPS
        if not by_group[gid]
    ]
    return {
        "expected_groups": expected_subject_groups(),
        "covered": covered,
        "missing": missing,
        "complete": len(missing) == 0,
    }


def build_pedagogy_golden_report(*, fixtures: list[dict], coverage: dict, passed: int, total: int) -> str:
    lines = [f"Golden Set: {passed}/{total} Fixtures bestanden"]
    if coverage.get("complete"):
        lines.append("Fachgruppen: alle abgedeckt (math, language, nmg, german, nature)")
    elif coverage.get("missing"):
        labels = ", ".join(row["label"] for row in coverage["missing"])
        lines.append(f"Fachgruppen ohne Fixture: {labels}")
    for row in fixtures:
        status = "OK" if row.get("ok") else "FEHLER"
        group = row.get("subject_group_label") or row.get("subject_group") or "—"
        err = f" — {row['error']}" if row.get("error") else ""
        lines.append(f"- {row['name']} ({group}): {status}{err}")
    return "\n".join(lines)


def run_pedagogy_golden_suite() -> dict:
    fixtures = list_pedagogy_golden_fixtures()
    passed = sum(1 for row in fixtures if row.get("ok"))
    coverage = pedagogy_golden_coverage(fixtures)
    total = len(fixtures)
    failed = total - passed
    return {
        "total": total,
        "passed": passed,
        "failed": failed,
        "fixtures": fixtures,
        "coverage": coverage,
        "coverage_complete": coverage["complete"],
        "ok": failed == 0 and coverage["complete"],
        "report": build_pedagogy_golden_report(
            fixtures=fixtures,
            coverage=coverage,
            passed=passed,
            total=total,
        ),
    }


def get_pedagogy_golden_status() -> dict:
    result = run_pedagogy_golden_suite()
    return {
        "fixtures": result["fixtures"],
        "coverage": result["coverage"],
        "total": result["total"],
        "passed": result["passed"],
        "failed": result["failed"],
        "coverage_complete": result["coverage_complete"],
        "ok": result["ok"],
        "report": result["report"],
    }
