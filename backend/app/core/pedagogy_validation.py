"""Didaktik-Abdeckung: weiche Hinweise und optionale harte Prüfung."""

from __future__ import annotations

import logging

from app.ai.providers import LlmError
from app.core.pedagogy_labels import (
    collect_content_blob,
    count_label_coverage,
    label_in_text,
    material_labels_from_methods,
)

_log = logging.getLogger(__name__)


def assess_pedagogy_coverage(modules: list, pedagogy_profile: dict) -> dict:
    profile = pedagogy_profile if isinstance(pedagogy_profile, dict) else {}
    methods = profile.get("methods") or []
    labels = material_labels_from_methods(methods if isinstance(methods, list) else [])
    blob = collect_content_blob(modules)
    warnings: list[str] = []

    matched_labels = count_label_coverage(labels, blob)
    if len(labels) >= 2 and matched_labels < min(2, len(labels)):
        warnings.append(
            f"labels_underrepresented:{matched_labels}/{len(labels)}"
        )

    for pattern in profile.get("exercise_patterns") or []:
        text = str(pattern or "").strip()
        if text and not label_in_text(text, blob):
            warnings.append(f"exercise_pattern_missing:{text[:80]}")

    worked = profile.get("worked_examples") or []
    if isinstance(worked, list) and worked:
        referenced = 0
        for item in worked:
            if not isinstance(item, dict):
                continue
            problem = str(item.get("problem") or "").strip()
            method_label = str(item.get("method_label") or item.get("label") or "").strip()
            if problem and problem[:24] in blob:
                referenced += 1
            elif method_label and label_in_text(method_label, blob):
                referenced += 1
        if referenced == 0:
            warnings.append("worked_examples_not_referenced")

    return {
        "labels": labels,
        "labels_matched": matched_labels,
        "warnings": warnings,
    }


def log_pedagogy_coverage_warnings(modules: list, pedagogy_profile: dict, *, unit_id: str = "") -> list[str]:
    result = assess_pedagogy_coverage(modules, pedagogy_profile)
    prefix = f"unit_id={unit_id} " if unit_id else ""
    for warning in result["warnings"]:
        _log.warning("pedagogy_coverage %s%s", prefix, warning)
    return result["warnings"]


def enforce_label_coverage(modules: list, pedagogy_profile: dict) -> None:
    """Harte Prüfung: mindestens zwei Heft-Labels im generierten Inhalt."""
    profile = pedagogy_profile if isinstance(pedagogy_profile, dict) else {}
    methods = profile.get("methods") or []
    if not isinstance(methods, list) or len(methods) < 2:
        return
    labels = material_labels_from_methods(methods)
    if len(labels) < 2:
        return
    blob = collect_content_blob(modules)
    matched = count_label_coverage(labels, blob)
    if matched < min(2, len(labels)):
        raise LlmError(
            "Zu wenig Lösungswege aus dem Heft in Karten/Quiz — Didaktik nicht ausreichend umgesetzt",
            "thin_content",
        )
