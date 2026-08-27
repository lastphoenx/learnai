"""Golden-Set-Fixtures für generierte Lerneinheiten (Repo-only, Admin read-only)."""

from __future__ import annotations

import json
import re
from pathlib import Path

from app.ai.errors import LlmError
from app.ai.generate import _validate_modules
from app.ai.task_types import UNIT_TASK_TYPES
from app.ai.validators.interactive import validate_interactive_modules
from app.core.pedagogy_labels import is_schema_placeholder
from app.core.quiz_explanation import explanation_has_derivation

_BUNDLED_DIR = Path(__file__).resolve().parent.parent / "fixtures" / "task_type_golden"
_EXPECTED_TASK_TYPES = [str(item["key"]) for item in UNIT_TASK_TYPES]
_TASK_TYPE_LABELS = {str(item["key"]): str(item["label"]) for item in UNIT_TASK_TYPES}
_EXAM_FORBIDDEN_KEYS = frozenset({"hint", "explanation", "help", "solution", "worked_solution"})
_VOCAB_LINE = re.compile(
    r"(?i)(wort|vokabel|term).{0,40}(bedeutung|übersetzung)|"
    r".+\s[-–—]\s.+\s[-–—]\s.+beispiel",
)


class TaskTypeGoldenError(Exception):
    def __init__(self, message: str, code: str = "invalid"):
        super().__init__(message)
        self.message = message
        self.code = code


def expected_task_types() -> list[dict]:
    return [{"id": key, "label": _TASK_TYPE_LABELS[key]} for key in _EXPECTED_TASK_TYPES]


def _module_questions(module: dict) -> list[dict]:
    quiz = module.get("quiz") if isinstance(module.get("quiz"), dict) else {}
    questions = quiz.get("questions") if isinstance(quiz.get("questions"), list) else []
    return [q for q in questions if isinstance(q, dict)]


def _validate_exam_modules(modules: list, *, fixture_name: str) -> None:
    for index, module in enumerate(modules):
        for q_index, question in enumerate(_module_questions(module)):
            for key in _EXAM_FORBIDDEN_KEYS:
                value = question.get(key)
                if value not in (None, ""):
                    raise TaskTypeGoldenError(
                        f"{fixture_name}: Modul {index + 1}, Frage {q_index + 1} "
                        f"enthält verbotenes Feld «{key}» (Kurzprüfung ohne Hilfen)",
                        "validation_failed",
                    )


def _validate_vocab_modules(modules: list, *, fixture_name: str) -> None:
    for index, module in enumerate(modules):
        content = module.get("content") if isinstance(module.get("content"), dict) else {}
        text = str(content.get("text") or "")
        practice = content.get("practice") if isinstance(content.get("practice"), list) else []
        has_vocab_text = bool(_VOCAB_LINE.search(text)) or (
            "bedeutung" in text.lower() and "beispiel" in text.lower()
        )
        has_vocab_practice = any(
            isinstance(item, dict)
            and str(item.get("prompt") or "").strip()
            and str(item.get("answer") or "").strip()
            for item in practice
        )
        if not has_vocab_text and not has_vocab_practice:
            raise TaskTypeGoldenError(
                f"{fixture_name}: Modul {index + 1} enthält keine erkennbaren Vokabel-Einträge "
                "(Wort, Bedeutung, Beispiel)",
                "validation_failed",
            )


def _validate_derivation_on_explained_questions(
    modules: list,
    *,
    fixture_name: str,
    task_type: str,
) -> int:
    checked = 0
    for index, module in enumerate(modules):
        for q_index, question in enumerate(_module_questions(module)):
            explanation = str(question.get("explanation") or "").strip()
            if not explanation:
                continue
            if is_schema_placeholder(explanation):
                raise TaskTypeGoldenError(
                    f"{fixture_name}: Modul {index + 1}, Frage {q_index + 1} "
                    "hat Schema-Platzhalter in der Erklärung",
                    "validation_failed",
                )
            q_text = str(question.get("q") or "")
            if not explanation_has_derivation(explanation, q_text):
                raise TaskTypeGoldenError(
                    f"{fixture_name}: Modul {index + 1}, Frage {q_index + 1} "
                    f"({task_type}) — Erklärung ohne nachvollziehbare Zwischenrechnung",
                    "validation_failed",
                )
            checked += 1
    return checked


def _validate_no_schema_placeholders(modules: list, *, fixture_name: str) -> None:
    for index, module in enumerate(modules):
        title = str(module.get("title") or "")
        if is_schema_placeholder(title):
            raise TaskTypeGoldenError(
                f"{fixture_name}: Modul {index + 1} hat Platzhalter-Titel",
                "validation_failed",
            )
        content = module.get("content") if isinstance(module.get("content"), dict) else {}
        text = str(content.get("text") or "")
        if text and is_schema_placeholder(text):
            raise TaskTypeGoldenError(
                f"{fixture_name}: Modul {index + 1} enthält Schema-Platzhalter im Text",
                "validation_failed",
            )


def validate_task_type_fixture(
    payload: dict,
    *,
    task_type: str,
    fixture_name: str = "fixture",
    min_cards: int = 8,
    min_questions: int = 8,
) -> dict:
    if task_type not in _EXPECTED_TASK_TYPES:
        raise TaskTypeGoldenError(f"Unbekannter task_type {task_type!r}", "invalid")

    modules = payload.get("modules")
    if not isinstance(modules, list) or not modules:
        raise TaskTypeGoldenError(f"{fixture_name}: modules-Liste fehlt oder ist leer", "validation_failed")

    _validate_no_schema_placeholders(modules, fixture_name=fixture_name)

    derivation_checked = 0
    try:
        if task_type == "interactive":
            validate_interactive_modules(
                modules,
                min_cards=min_cards,
                min_questions=min_questions,
            )
            derivation_checked = _validate_derivation_on_explained_questions(
                modules,
                fixture_name=fixture_name,
                task_type=task_type,
            )
        else:
            _validate_modules(modules, task=task_type)
            if task_type == "exam":
                _validate_exam_modules(modules, fixture_name=fixture_name)
            elif task_type == "vocab":
                _validate_vocab_modules(modules, fixture_name=fixture_name)
            elif task_type in {"math", "mixed", "practice"}:
                derivation_checked = _validate_derivation_on_explained_questions(
                    modules,
                    fixture_name=fixture_name,
                    task_type=task_type,
                )
    except LlmError as exc:
        raise TaskTypeGoldenError(f"{fixture_name}: {exc.message}", "validation_failed") from exc

    question_count = sum(len(_module_questions(module)) for module in modules)
    card_count = 0
    if task_type == "interactive":
        for module in modules:
            content = module.get("content") if isinstance(module.get("content"), dict) else {}
            cards = content.get("cards") if isinstance(content.get("cards"), list) else []
            card_count += len(cards)

    return {
        "ok": True,
        "task_type": task_type,
        "module_count": len(modules),
        "question_count": question_count,
        "card_count": card_count,
        "derivation_checked": derivation_checked,
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
    task_type = str(meta.get("task_type") or "").strip() or None
    subject_hint = str(meta.get("subject_hint") or "").strip() or None
    min_cards = int(meta.get("min_cards") or 8)
    min_questions = int(meta.get("min_questions") or 8)
    body = {k: v for k, v in payload.items() if k != "_meta"}

    row: dict = {
        "name": path.stem,
        "file": path.name,
        "task_type": task_type,
        "task_type_label": _TASK_TYPE_LABELS.get(task_type or "", task_type),
        "subject_hint": subject_hint,
        "min_cards": min_cards,
        "min_questions": min_questions,
    }

    if not task_type:
        row["ok"] = False
        row["error"] = "_meta.task_type fehlt"
        return row

    if task_type not in _EXPECTED_TASK_TYPES:
        row["ok"] = False
        row["error"] = f"Unbekannter task_type {task_type!r}"
        return row

    try:
        result = validate_task_type_fixture(
            body,
            task_type=task_type,
            fixture_name=path.stem,
            min_cards=min_cards,
            min_questions=min_questions,
        )
        row["ok"] = True
        row.update(result)
    except TaskTypeGoldenError as exc:
        row["ok"] = False
        row["error"] = exc.message

    return row


def list_task_type_golden_fixtures() -> list[dict]:
    if not _BUNDLED_DIR.is_dir():
        return []
    return [_read_fixture_meta(path) for path in sorted(_BUNDLED_DIR.glob("*.json"))]


def task_type_golden_coverage(fixtures: list[dict] | None = None) -> dict:
    rows = fixtures if fixtures is not None else list_task_type_golden_fixtures()
    by_type: dict[str, list[str]] = {key: [] for key in _EXPECTED_TASK_TYPES}
    for row in rows:
        task_type = row.get("task_type")
        if task_type in by_type:
            by_type[task_type].append(row["name"])

    covered = [
        {
            "id": key,
            "label": _TASK_TYPE_LABELS[key],
            "fixtures": by_type[key],
        }
        for key in _EXPECTED_TASK_TYPES
        if by_type[key]
    ]
    missing = [
        {"id": key, "label": _TASK_TYPE_LABELS[key]}
        for key in _EXPECTED_TASK_TYPES
        if not by_type[key]
    ]
    return {
        "expected_types": expected_task_types(),
        "covered": covered,
        "missing": missing,
        "complete": len(missing) == 0,
    }


def build_task_type_golden_report(*, fixtures: list[dict], coverage: dict, passed: int, total: int) -> str:
    lines = [f"Aufgabentyp Golden Set: {passed}/{total} Fixtures bestanden"]
    if coverage.get("complete"):
        lines.append("Aufgabentypen: alle abgedeckt")
    elif coverage.get("missing"):
        labels = ", ".join(row["label"] for row in coverage["missing"])
        lines.append(f"Aufgabentypen ohne Fixture: {labels}")
    lines.append(
        "Grenze: prüft Struktur/Qualitätsregeln am eingefrorenen Beispiel — "
        "nicht ob die Live-KI heute noch genauso gut generiert."
    )
    for row in fixtures:
        status = "OK" if row.get("ok") else "FEHLER"
        label = row.get("task_type_label") or row.get("task_type") or "—"
        err = f" — {row['error']}" if row.get("error") else ""
        lines.append(f"- {row['name']} ({label}): {status}{err}")
    return "\n".join(lines)


def run_task_type_golden_suite() -> dict:
    fixtures = list_task_type_golden_fixtures()
    passed = sum(1 for row in fixtures if row.get("ok"))
    coverage = task_type_golden_coverage(fixtures)
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
        "report": build_task_type_golden_report(
            fixtures=fixtures,
            coverage=coverage,
            passed=passed,
            total=total,
        ),
    }


def get_task_type_golden_status() -> dict:
    result = run_task_type_golden_suite()
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
