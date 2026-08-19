"""KI-Analyse korrigierter Schulprüfungen (Phase B)."""

from __future__ import annotations

from pathlib import Path

from app.ai.catalog import resolve_task_ai
from app.ai.errors import LlmError
from app.ai.extract import extract_pdf_text
from app.ai.providers import complete, describe_image, parse_json_object, resolve_provider

ANALYSIS_SYSTEM = (
    "Du bist Lernberater für Eltern und Kinder. Antworte immer mit einem JSON-Objekt, ohne Markdown."
    ' Schema: {"summary":"...","strengths":["..."],"gaps":["..."],'
    '"error_patterns":[{"tag":"snake_case","label":"...","count":1,"examples":["..."]}],'
    '"tasks":[{"index":1,"description":"...","correct":false,"points_earned":0,'
    '"max_points":5,"errors":["..."]}],"recommendations":["..."]}'
    " error_patterns: konkrete Fehlertypen (z.B. fractions_denominator, unit_conversion)."
    " recommendations: 2–5 konkrete Lernschritte zur Nacharbeit."
)


def _image_mime(path: Path, content_type: str | None) -> str:
    if content_type and content_type.startswith("image/"):
        return content_type
    ext = path.suffix.lower()
    if ext in {".png"}:
        return "image/png"
    if ext in {".webp"}:
        return "image/webp"
    if ext in {".gif"}:
        return "image/gif"
    return "image/jpeg"


def _extract_exam_text(
    path: Path,
    content_type: str | None,
    *,
    vision_provider: str,
    vision_model: str | None,
) -> str:
    if content_type == "application/pdf" or path.suffix.lower() == ".pdf":
        return extract_pdf_text(path)
    if (content_type or "").startswith("image/") or path.suffix.lower() in {
        ".jpg",
        ".jpeg",
        ".png",
        ".webp",
        ".gif",
    }:
        data = path.read_bytes()
        mime = _image_mime(path, content_type)
        result = describe_image(
            image_bytes=data,
            mime=mime,
            prompt=(
                "Lies diese korrigierte Schulprüfung vollständig. "
                "Extrahiere alle Aufgaben, Schülerantworten, Korrekturen (Rotstift), "
                "Punkteabzüge und Notizen der Lehrperson."
            ),
            provider=vision_provider,
            model=vision_model,
        )
        return result["text"]
    raise LlmError("Dateityp für Prüfungsanalyse nicht unterstützt (PDF oder Bild)", "bad_file")


def analyze_exam_content(
    path: Path,
    *,
    content_type: str | None,
    subject: str | None,
    unit_title: str,
    grade_label: str | None,
    score: int | None,
    max_score: int | None,
    teacher_notes: str | None,
    prefs: dict | None = None,
    provider: str | None = None,
) -> dict:
    prefs = prefs or {}
    vision_provider, vision_model = resolve_task_ai(prefs, "vision", override=provider)
    analysis_provider, analysis_model = resolve_task_ai(prefs, "exam_analysis", override=provider)
    vision_provider = resolve_provider(vision_provider)
    analysis_provider = resolve_provider(analysis_provider)

    raw = _extract_exam_text(
        path,
        content_type,
        vision_provider=vision_provider,
        vision_model=vision_model,
    )
    if len(raw.strip()) < 20:
        raise LlmError("Zu wenig erkennbarer Inhalt in der Prüfung", "empty_content")

    score_line = ""
    if score is not None and max_score is not None:
        score_line = f"Ergebnis: {score}/{max_score} Punkte."
    elif grade_label:
        score_line = f"Note: {grade_label}."

    prompt = (
        f"Analysiere diese korrigierte Schulprüfung zum Thema «{unit_title}».\n"
        f"Fach: {subject or 'offen'}\n"
        f"{score_line}\n"
        f"Hinweis der Lehrperson: {teacher_notes or '(keiner)'}\n\n"
        f"Inhalt der Prüfung (OCR/Vision):\n{raw[:12000]}\n"
    )
    result = complete(
        prompt=prompt,
        provider=analysis_provider,
        system=ANALYSIS_SYSTEM,
        model=analysis_model,
    )
    parsed = parse_json_object(result["text"])
    parsed["provider"] = result["provider"]
    parsed["model"] = result["model"]
    return parsed
