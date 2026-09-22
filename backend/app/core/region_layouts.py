"""Vordefinierte isometrische Flächen für region_paint (keine Foto-Polygone)."""

from __future__ import annotations

from typing import Any

# Punkte als [x, y] in 0–1 relativ zum viewBox des Templates.
REGION_TEMPLATES: dict[str, dict[str, Any]] = {
    "iso_single_cube": {
        "title": "Würfel (isometrisch)",
        "view_width": 400,
        "view_height": 280,
        "regions": [
            {
                "id": "top",
                "label": "Oberseite",
                "points": [[0.32, 0.12], [0.68, 0.12], [0.78, 0.26], [0.42, 0.26]],
            },
            {
                "id": "left",
                "label": "Linke Seite",
                "points": [[0.22, 0.26], [0.42, 0.26], [0.42, 0.72], [0.22, 0.72]],
            },
            {
                "id": "right",
                "label": "Rechte Seite",
                "points": [[0.42, 0.26], [0.78, 0.26], [0.78, 0.72], [0.42, 0.72]],
            },
        ],
    },
    "iso_tower_2": {
        "title": "Zwei Würfel übereinander",
        "view_width": 400,
        "view_height": 300,
        "regions": [
            {
                "id": "lower_top",
                "label": "Unten — Deckel",
                "points": [[0.30, 0.38], [0.62, 0.38], [0.70, 0.48], [0.38, 0.48]],
            },
            {
                "id": "lower_left",
                "label": "Unten — links",
                "points": [[0.20, 0.48], [0.38, 0.48], [0.38, 0.78], [0.20, 0.78]],
            },
            {
                "id": "lower_right",
                "label": "Unten — rechts",
                "points": [[0.38, 0.48], [0.70, 0.48], [0.70, 0.78], [0.38, 0.78]],
            },
            {
                "id": "upper_top",
                "label": "Oben — Deckel",
                "points": [[0.30, 0.10], [0.62, 0.10], [0.70, 0.20], [0.38, 0.20]],
            },
            {
                "id": "upper_left",
                "label": "Oben — links",
                "points": [[0.20, 0.20], [0.38, 0.20], [0.38, 0.38], [0.20, 0.38]],
            },
            {
                "id": "upper_right",
                "label": "Oben — rechts",
                "points": [[0.38, 0.20], [0.70, 0.20], [0.70, 0.38], [0.38, 0.38]],
            },
        ],
    },
}


def get_region_template(template_id: str) -> dict[str, Any] | None:
    key = str(template_id or "").strip()
    if not key:
        return None
    tpl = REGION_TEMPLATES.get(key)
    if not tpl:
        return None
    return dict(tpl)


def list_region_template_ids() -> list[str]:
    return sorted(REGION_TEMPLATES.keys())
