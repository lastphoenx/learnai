"""PDF-Export: Elternbericht und Arbeitsblatt (PyMuPDF Story)."""

from __future__ import annotations

import html
import io
import re
import uuid
from datetime import datetime, timezone

import fitz
from sqlalchemy.orm import Session

from app.models import User
from app.services.exam_insights_service import exam_insights_for_profile
from app.services.profile_service import get_profile_for_actor
from app.services.unit_service import UnitError, _get_unit_or_404, get_unit

_PDF_CSS = """
body { font-family: sans-serif; font-size: 11pt; line-height: 1.45; color: #1a1a1a; }
h1 { font-size: 18pt; margin: 0 0 0.4em; }
h2 { font-size: 13pt; margin: 1.2em 0 0.4em; border-bottom: 1px solid #ccc; padding-bottom: 0.2em; }
h3 { font-size: 11.5pt; margin: 0.8em 0 0.3em; }
p, li { margin: 0.25em 0; }
.meta { color: #555; font-size: 9.5pt; }
.muted { color: #666; }
.alert { background: #fff8e6; border: 1px solid #e6c200; padding: 0.5em 0.75em; margin: 0.5em 0; }
.module { margin-top: 1em; page-break-inside: avoid; }
.question { margin: 0.6em 0 0.8em 1em; }
.flashcard-table { width: 100%; border-collapse: collapse; margin: 0.6em 0 1em; font-size: 10.5pt; }
.flashcard-table th { background: #eee; border: 1px solid #bbb; padding: 0.35em 0.55em; text-align: left; font-size: 9.5pt; }
.flashcard-table td { border: 1px solid #bbb; padding: 0.45em 0.6em; vertical-align: top; width: 50%; }
.knowledge-item { margin: 0.45em 0; padding: 0.55em 0.75em; background: #f4f4f4; border-left: 3px solid #999; page-break-inside: avoid; }
.knowledge-item strong { display: block; margin-bottom: 0.15em; }
.card-tip { display: block; margin-top: 0.25em; font-size: 9pt; color: #666; font-style: italic; }
.solutions { margin-top: 1.5em; page-break-before: always; }
.solutions li { margin: 0.2em 0; }
.answer-line { border-bottom: 1px solid #999; height: 1.4em; margin: 0.35em 0; }
.footer { margin-top: 2em; font-size: 9pt; color: #888; }
ul { padding-left: 1.2em; }
"""

_TRANSFER_LABELS = {
    "transfer_gap": "In der App deutlich besser als in der Prüfung (Transferproblem möglich).",
    "exam_better": "In der Prüfung besser als im App-Quiz.",
    "aligned": "App-Quiz und Prüfung liegen nah beieinander.",
    "quiz_only": "Nur App-Quiz — noch keine vergleichbare Prüfung.",
    "exam_only": "Nur Prüfung — kein auswertbares App-Quiz.",
}


def _esc(text: str | None) -> str:
    return html.escape(text or "", quote=True)


def _nl2br(text: str) -> str:
    return _esc(text).replace("\n", "<br/>")


def _slug_filename(name: str, *, suffix: str) -> str:
    base = re.sub(r"[^\w\-]+", "-", name.strip().lower(), flags=re.UNICODE)
    base = re.sub(r"-+", "-", base).strip("-") or "export"
    return f"{base[:48]}-{suffix}.pdf"


def html_to_pdf(html_body: str) -> bytes:
    """HTML-Fragment (+ CSS) → PDF-Bytes (A4)."""
    doc_html = f"<html><head><style>{_PDF_CSS}</style></head><body>{html_body}</body></html>"
    buffer = io.BytesIO()
    writer = fitz.DocumentWriter(buffer)
    story = fitz.Story(html=doc_html)
    mediabox = fitz.paper_rect("a4")
    where = mediabox + (42, 42, -42, -42)
    more = True
    while more:
        page = writer.begin_page(mediabox)
        more, _ = story.place(where)
        story.draw(page)
        writer.end_page()
    writer.close()
    return buffer.getvalue()


def _transfer_line(transfer: dict | None) -> str:
    if not transfer:
        return ""
    parts: list[str] = []
    if transfer.get("quiz_total"):
        q_pct = transfer.get("quiz_percent")
        parts.append(
            f"App-Quiz {transfer['quiz_correct']}/{transfer['quiz_total']}"
            + (f" ({q_pct}%)" if q_pct is not None else "")
        )
    if transfer.get("exam_max_score") is not None and transfer.get("exam_score") is not None:
        e_pct = transfer.get("exam_percent")
        parts.append(
            f"Prüfung {transfer['exam_score']}/{transfer['exam_max_score']}"
            + (f" ({e_pct}%)" if e_pct is not None else "")
        )
    if transfer.get("gap_percent") is not None:
        gap = transfer["gap_percent"]
        parts.append(f"Differenz {gap:+d} %")
    line = " · ".join(parts)
    signal = transfer.get("signal")
    hint = _TRANSFER_LABELS.get(signal or "", "")
    if hint:
        return f'<p class="muted">{_esc(line)} — {_esc(hint)}</p>'
    return f'<p class="muted">{_esc(line)}</p>' if line else ""


def build_child_report_html(db: Session, user: User, profile_id: uuid.UUID) -> str:
    profile = get_profile_for_actor(db, user, profile_id)
    insights = exam_insights_for_profile(db, user.tenant_id, profile.id)
    created = datetime.now(timezone.utc).strftime("%d.%m.%Y")

    parts = [
        f"<h1>Lernbericht — {_esc(profile.display_name)}</h1>",
        f'<p class="meta">Erstellt am {created}</p>',
        "<h2>Schulprüfungen</h2>",
    ]
    if not insights["timeline"]:
        parts.append("<p>Noch keine Prüfungen erfasst.</p>")
    else:
        parts.append("<ul>")
        for row in insights["timeline"]:
            date = (row.get("taken_at") or "")[:10]
            grade = row.get("grade_label") or "—"
            title = row.get("unit_title") or "Ohne Einheit"
            status = "analysiert" if row.get("has_analysis") else "ohne Analyse"
            item = (
                f"<strong>{_esc(date)}</strong>: {_esc(title)} — {_esc(grade)} ({_esc(status)})"
            )
            transfer_html = _transfer_line(row.get("transfer"))
            if transfer_html:
                item += (
                    transfer_html.replace('<p class="muted">', '<br/><span class="muted">')
                    .replace("</p>", "</span>")
                )
            parts.append(f"<li>{item}</li>")
        parts.append("</ul>")

    parts.append("<h2>Häufige Fehlermuster</h2>")
    if not insights["error_tags"]:
        parts.append("<p>Keine Fehlermuster aus Analysen.</p>")
    else:
        parts.append("<ul>")
        for row in insights["error_tags"]:
            parts.append(
                f"<li>{_esc(row['label'])} ({_esc(row['tag'])}): "
                f"{row['count']}× in {row['exam_count']} Prüfung(en)</li>"
            )
        parts.append("</ul>")

    parts.append("<h2>Wiederholung empfohlen</h2>")
    if not insights["review_due"]:
        parts.append("<p>Keine fälligen Wiederholungen (Schwelle: 7 Tage nach Abschluss).</p>")
    else:
        parts.append("<ul>")
        for row in insights["review_due"]:
            parts.append(
                f"<li><strong>{_esc(row['title'])}</strong> — vor {row['days_since']} Tagen abgeschlossen</li>"
            )
        parts.append("</ul>")

    if insights["pending_remediation"]:
        parts.append(
            f'<p class="alert">{insights["pending_remediation"]} analysierte Prüfung(en) '
            "ohne erstellte Nacharbeit-Einheit.</p>"
        )

    parts.append('<p class="footer">LearnAI — Elternbericht</p>')
    return "\n".join(parts)


def child_report_pdf(db: Session, user: User, profile_id: uuid.UUID) -> tuple[bytes, str]:
    profile = get_profile_for_actor(db, user, profile_id)
    html_body = build_child_report_html(db, user, profile_id)
    pdf = html_to_pdf(html_body)
    filename = _slug_filename(profile.display_name, suffix="bericht")
    return pdf, filename


def build_unit_worksheet_html(unit: dict) -> str:
    if _is_interactive_unit(unit):
        return build_interactive_trainer_worksheet_html(unit)
    return build_classic_worksheet_html(unit)


def _is_interactive_unit(unit: dict) -> bool:
    if (unit.get("task_type") or "") == "interactive":
        return True
    for mod in unit.get("modules") or []:
        content = mod.get("content") if isinstance(mod.get("content"), dict) else {}
        if isinstance(content, dict) and content.get("cards"):
            return True
    return False


def _worksheet_header_parts(unit: dict, *, subtitle: str) -> list[str]:
    parts = [
        f"<h1>{_esc(unit.get('title') or 'Lerneinheit')}</h1>",
        f'<p class="meta">{_esc(subtitle)}</p>',
    ]
    if unit.get("learner_name"):
        parts.append(f"<p><strong>Lernende/r:</strong> {_esc(unit['learner_name'])}</p>")
    meta_bits = []
    if unit.get("subject"):
        meta_bits.append(_esc(unit["subject"]))
    if unit.get("target_age"):
        meta_bits.append(f"{_esc(unit['target_age'])} J.")
    meta_bits.append(f"Stufe {unit.get('difficulty', 1)}")
    if meta_bits:
        parts.append(f'<p class="muted">{" · ".join(meta_bits)}</p>')
    if unit.get("brief"):
        parts.append(f"<p>{_nl2br(unit['brief'])}</p>")
    return parts


def _append_quiz_questions_html(
    parts: list[str],
    questions: list,
    *,
    global_offset: int = 0,
    answer_lines: int = 1,
) -> int:
    """Quiz ohne Lösungen im Hauptteil. Gibt neue Gesamtzahl der Fragen zurück."""
    count = 0
    if not isinstance(questions, list) or not questions:
        return global_offset
    for qi, q in enumerate(questions, start=1):
        if not isinstance(q, dict):
            continue
        num = global_offset + qi
        prompt = (q.get("q") or "").strip() or f"Frage {num}"
        parts.append(f'<div class="question"><p><strong>{num}.</strong> {_esc(prompt)}</p>')
        options = q.get("options") or []
        if isinstance(options, list) and options:
            parts.append("<ul>")
            for oi, opt in enumerate(options):
                letter = chr(ord("a") + oi)
                parts.append(f"<li>{letter}) {_esc(str(opt))}</li>")
            parts.append("</ul>")
        for _ in range(max(1, answer_lines)):
            parts.append('<div class="answer-line"></div>')
        parts.append("</div>")
        count += 1
    return global_offset + count


def build_classic_worksheet_html(unit: dict) -> str:
    modules = unit.get("modules") or []
    if not modules:
        raise UnitError("Keine Lernblöcke — zuerst mit KI aufbereiten", "no_modules")

    parts = _worksheet_header_parts(unit, subtitle="Arbeitsblatt zum Ausdrucken")
    quiz_total = 0

    for i, mod in enumerate(modules, start=1):
        title = mod.get("title") or f"Block {i}"
        parts.append(f'<div class="module"><h2>{i}. {_esc(title)}</h2>')
        content = mod.get("content") if isinstance(mod.get("content"), dict) else {}
        text = (content.get("text") or "").strip() if isinstance(content, dict) else ""
        if text:
            parts.append(f"<p>{_nl2br(text)}</p>")

        quiz = mod.get("quiz") if isinstance(mod.get("quiz"), dict) else {}
        questions = quiz.get("questions") if isinstance(quiz, dict) else []
        if isinstance(questions, list) and questions:
            parts.append("<h3>Übungen / Fragen</h3>")
            quiz_total = _append_quiz_questions_html(
                parts, questions, global_offset=quiz_total, answer_lines=2
            )
        parts.append("</div>")

    parts.append('<p class="footer">LearnAI — Arbeitsblatt (ohne Lösungen)</p>')
    return "\n".join(parts)


def build_interactive_trainer_worksheet_html(unit: dict) -> str:
    modules = unit.get("modules") or []
    if not modules:
        raise UnitError("Keine Lernblöcke — zuerst mit KI aufbereiten", "no_modules")

    parts = _worksheet_header_parts(unit, subtitle="Lerntrainer — Arbeitsblatt zum Ausdrucken")
    quiz_total = 0
    quiz_solutions: list[str] = []
    card_count = 0

    for i, mod in enumerate(modules, start=1):
        title = mod.get("title") or f"Bereich {i}"
        parts.append(f'<div class="module"><h2>{i}. {_esc(title)}</h2>')
        content = mod.get("content") if isinstance(mod.get("content"), dict) else {}

        intro = (content.get("intro") or "").strip() if isinstance(content, dict) else ""
        if intro:
            parts.append(f"<p>{_nl2br(intro)}</p>")

        knowledge = content.get("knowledge") if isinstance(content, dict) else []
        if isinstance(knowledge, list) and knowledge:
            parts.append("<h3>Kernwissen</h3>")
            for item in knowledge:
                if not isinstance(item, dict):
                    continue
                k_title = (item.get("title") or "").strip()
                k_text = (item.get("text") or "").strip()
                if not k_text and not k_title:
                    continue
                inner = f"<strong>{_esc(k_title)}</strong>" if k_title else ""
                if k_text:
                    inner += f"<p style='margin:0.2em 0 0'>{_nl2br(k_text)}</p>"
                parts.append(f'<div class="knowledge-item">{inner}</div>')

        cards = content.get("cards") if isinstance(content, dict) else []
        if isinstance(cards, list) and cards:
            parts.append("<h3>Lernkarten</h3>")
            parts.append(
                '<table class="flashcard-table"><thead><tr>'
                "<th>Frage</th><th>Antwort</th>"
                "</tr></thead><tbody>"
            )
            for card in cards:
                if not isinstance(card, dict):
                    continue
                question = (card.get("question") or "").strip()
                answer = (card.get("answer") or "").strip()
                if not question and not answer:
                    continue
                card_count += 1
                tip = (card.get("tip") or "").strip()
                answer_cell = _esc(answer) if answer else "—"
                if tip:
                    answer_cell += f'<span class="card-tip">Tipp: {_esc(tip)}</span>'
                parts.append(
                    f"<tr><td>{_esc(question or '—')}</td><td>{answer_cell}</td></tr>"
                )
            parts.append("</tbody></table>")

        quiz = mod.get("quiz") if isinstance(mod.get("quiz"), dict) else {}
        questions = quiz.get("questions") if isinstance(quiz, dict) else []
        if isinstance(questions, list) and questions:
            parts.append("<h3>Quiz</h3>")
            before = quiz_total
            quiz_total = _append_quiz_questions_html(parts, questions, global_offset=quiz_total)
            for qi, q in enumerate(questions, start=1):
                if not isinstance(q, dict):
                    continue
                num = before + qi
                options = q.get("options") or []
                answer_idx = int(q.get("answer") or 0)
                if isinstance(options, list) and 0 <= answer_idx < len(options):
                    letter = chr(ord("a") + answer_idx)
                    quiz_solutions.append(f"{num}. {letter}) {_esc(str(options[answer_idx]))}")
                else:
                    quiz_solutions.append(f"{num}. —")
        parts.append("</div>")

    if quiz_solutions:
        parts.append('<div class="solutions"><h2>Quiz-Lösungen</h2><ul>')
        for line in quiz_solutions:
            parts.append(f"<li>{line}</li>")
        parts.append("</ul></div>")

    parts.append(
        f'<p class="footer">LearnAI — Lerntrainer ({card_count} Karten, {quiz_total} Quizfragen)</p>'
    )
    return "\n".join(parts)


def unit_worksheet_pdf(db: Session, user: User, unit_id: uuid.UUID) -> tuple[bytes, str]:
    unit = get_unit(db, user, unit_id)
    html_body = build_unit_worksheet_html(unit)
    pdf = html_to_pdf(html_body)
    suffix = "trainer-arbeitsblatt" if _is_interactive_unit(unit) else "arbeitsblatt"
    filename = _slug_filename(unit.get("title") or "einheit", suffix=suffix)
    return pdf, filename
