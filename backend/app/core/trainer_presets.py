"""Trainer-Umfangs-Presets für Lerntrainer-Generierung."""

from __future__ import annotations

from typing import Any

from app.schemas import TrainerOptionsSchema

TRAINER_PRESET_IDS = frozenset({"posten_compact", "standard", "exam_review", "custom"})

DEFAULT_PRESET_ID = "standard"
DEFAULT_BATCH_PRESET_ID = "posten_compact"

_PRESET_OPTIONS: dict[str, dict[str, Any]] = {
    "posten_compact": {
        "cards": 12,
        "questions": 8,
        "style": "exam",
        "answer_length": "short",
        "llm_provider": None,
    },
    "standard": {
        "cards": 50,
        "questions": 50,
        "style": "playful",
        "answer_length": "short",
        "llm_provider": None,
    },
    "exam_review": {
        "cards": 15,
        "questions": 28,
        "style": "exam",
        "answer_length": "short",
        "llm_provider": None,
    },
}

PRESET_LABELS: dict[str, str] = {
    "posten_compact": "Posten kompakt (~10–15 Min)",
    "standard": "Standard (tiefes Üben)",
    "exam_review": "Prüfung / Review",
    "custom": "Frei",
}

PRESET_HINTS: dict[str, str] = {
    "posten_compact": "Eine Doppelseite oder ein Heft-Posten — fokussiert, nicht überladen.",
    "standard": "Wie bisher: viele Karten und Quizfragen (z. B. Mathe).",
    "exam_review": "Quer-Wiederholung vor einer Lernzielkontrolle.",
    "custom": "Karten- und Quiz-Anzahl selbst wählen.",
}


def trainer_presets_public() -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for preset_id in ("posten_compact", "standard", "exam_review", "custom"):
        row: dict[str, Any] = {
            "id": preset_id,
            "label": PRESET_LABELS[preset_id],
            "hint": PRESET_HINTS[preset_id],
        }
        if preset_id != "custom":
            row["options"] = preset_options(preset_id)
        else:
            row["options"] = None
            row["limits"] = {"cards_min": 5, "cards_max": 100, "questions_min": 5, "questions_max": 100}
        out.append(row)
    return out


def preset_options(preset_id: str) -> dict[str, Any]:
    if preset_id not in _PRESET_OPTIONS:
        raise ValueError(f"Unbekanntes Preset: {preset_id}")
    return TrainerOptionsSchema.normalize_raw(dict(_PRESET_OPTIONS[preset_id])).model_dump()


def apply_trainer_preset(
    preset_id: str | None,
    *,
    overrides: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], str | None]:
    """Preset (+ optionale Overrides) → (trainer_options, gespeicherte preset_id)."""
    pid = (preset_id or DEFAULT_PRESET_ID).strip().lower()
    if pid not in TRAINER_PRESET_IDS:
        raise ValueError(f"Unbekanntes Preset: {pid}")

    if pid == "custom":
        base = preset_options(DEFAULT_PRESET_ID)
        if overrides:
            base.update({k: v for k, v in overrides.items() if v is not None})
        return TrainerOptionsSchema.normalize_raw(base).model_dump(), "custom"

    merged = dict(preset_options(pid))
    if overrides:
        merged.update({k: v for k, v in overrides.items() if v is not None})
    return TrainerOptionsSchema.normalize_raw(merged).model_dump(), pid


def detect_trainer_preset(options: dict[str, Any] | None) -> str:
    """Erkennt Preset anhand der Optionen — «custom» wenn keine exakte Übereinstimmung."""
    if not isinstance(options, dict):
        return DEFAULT_PRESET_ID
    normalized = TrainerOptionsSchema.normalize_raw(options).model_dump()
    for preset_id, raw in _PRESET_OPTIONS.items():
        if normalized == TrainerOptionsSchema.normalize_raw(dict(raw)).model_dump():
            return preset_id
    return "custom"


def default_trainer_options_for_task(task_type: str, *, preset_id: str | None = None) -> dict[str, Any]:
    if (task_type or "").strip().lower() != "interactive":
        return TrainerOptionsSchema().model_dump()
    opts, _ = apply_trainer_preset(preset_id or DEFAULT_PRESET_ID)
    return opts
