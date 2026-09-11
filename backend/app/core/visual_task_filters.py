"""Filter für Vision-visual_tasks — kreative Zeichenaufgaben und degenerierte Placements."""

from __future__ import annotations

import re
from typing import Any

from app.core.label_diagram import is_draw_format

_UNUSABLE_VISUAL_INSTRUCTION = re.compile(
    r"bild der|abbildung|foto|altstadt.*beschrif|landmark|"
    r"zeichne.*landschaft|nach deiner fantasie|"
    r"symbol.*gegenwart|zeichne.*symbol|typisch.*21|"
    r"leeres feld|deiner meinung|gegenstand.*typisch",
    re.I,
)


def is_unusable_visual_instruction(text: str) -> bool:
    return bool(_UNUSABLE_VISUAL_INSTRUCTION.search(str(text or "")))


def has_degenerate_placements(placements: list[Any]) -> bool:
    """Mehrere Begriffe auf identischen Koordinaten (Vision-Fallback 0.5/0.5)."""
    if not isinstance(placements, list) or len(placements) < 2:
        return False
    coords: list[tuple[float, float]] = []
    for item in placements:
        if not isinstance(item, dict):
            continue
        try:
            x = round(float(item.get("x", 0.5)), 2)
            y = round(float(item.get("y", 0.5)), 2)
        except (TypeError, ValueError):
            continue
        coords.append((x, y))
    return len(coords) >= 2 and len(set(coords)) < len(coords)


def filter_visual_task_entry(entry: dict[str, Any]) -> dict[str, Any] | None:
    """Entfernt unbrauchbare visual_tasks; strippt degenerierte placements."""
    instruction = str(entry.get("instruction") or "").strip()
    kind = str(entry.get("kind") or "").strip()
    if instruction and is_unusable_visual_instruction(instruction):
        return None
    if is_draw_format(kind) and instruction and is_unusable_visual_instruction(instruction):
        return None
    out = dict(entry)
    placements = out.get("placements")
    if isinstance(placements, list) and has_degenerate_placements(placements):
        out.pop("placements", None)
    return out
