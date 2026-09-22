"""QA-Hinweise für erwartete Raumaufgaben (Geometrie / posten_compact)."""

from __future__ import annotations

from app.ai.subject_focus import detect_focus_group
from app.core.focus_groups import normalize_focus_key
from app.core.spatial_compact import SPATIAL_ANSWER_TYPES, count_spatial_practice_in_modules
from app.models import LearningUnit
from app.services.crypto_json import decrypt_json
from app.services.unit_service import get_trainer_options


def _math_focus_geometry(math_focus: str | None) -> bool:
    key = normalize_focus_key(str(math_focus or ""))
    return key in ("geometry", "geometry_spatial")


def spatial_practice_counts_from_unit(unit: LearningUnit) -> dict[str, int]:
    modules: list[dict] = []
    for mod in unit.modules or []:
        content = decrypt_json(mod.content_encrypted) or {}
        modules.append({"title": mod.title, "content": content if isinstance(content, dict) else {}})
    total = count_spatial_practice_in_modules(modules)
    by_type: dict[str, int] = {t: 0 for t in SPATIAL_ANSWER_TYPES}
    for mod in modules:
        if str(mod.get("title") or "").strip() != "Aufgaben":
            continue
        for item in (mod.get("content") or {}).get("practice") or []:
            if not isinstance(item, dict):
                continue
            at = str(item.get("answer_type") or "")
            if at in by_type:
                by_type[at] += 1
    return {"total": total, **by_type}


def spatial_report_lines(unit: LearningUnit, recon: dict | None) -> list[str]:
    recon = recon if isinstance(recon, dict) else {}
    options = get_trainer_options(recon)
    preset = str(recon.get("trainer_preset") or options.get("trainer_preset") or "").strip()
    focus_group = (
        detect_focus_group(subject=unit.subject, task_type=str(unit.task_type or "interactive")) or ""
    )
    math_focus = recon.get("math_focus")
    counts = spatial_practice_counts_from_unit(unit)
    lines = ["## Raumaufgaben-QA", ""]
    lines.append(f"- Trainer-Preset: `{preset or 'standard'}`")
    lines.append(f"- Schwerpunkt: `{math_focus or '—'}`")
    lines.append(
        f"- Raum-Übungen in «Aufgaben»: **{counts['total']}** "
        f"(image_choice={counts.get('image_choice', 0)}, "
        f"point_on_image={counts.get('point_on_image', 0)}, "
        f"grid_fill={counts.get('grid_fill', 0)}, "
        f"region_paint={counts.get('region_paint', 0)})"
    )
    if preset not in ("posten_compact", "exam_review"):
        lines.append(
            "- Hinweis: `image_choice` / `point_on_image` / `grid_fill` / `region_paint` "
            "laufen nur über Preset **posten_compact** oder **exam_review**."
        )
    elif focus_group == "math" and _math_focus_geometry(str(math_focus) if math_focus else None):
        if counts["total"] < 1:
            lines.append(
                "- **WARNUNG:** Geometrie/Raum erwartet, aber keine Raum-Übungen — "
                "Generierung erneut mit Preset posten_compact oder Retry prüfen."
            )
        else:
            lines.append("- OK: Mindestens eine Raum-Übung vorhanden.")
    lines.append("")
    return lines
