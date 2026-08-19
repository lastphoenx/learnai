"""Phase D: Fehlertrends, Wiederholungs-Erinnerungen, Elternberichte."""

from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import datetime, timezone

from sqlalchemy.orm import Session, joinedload

from app.ai.error_tags import collect_tags_from_analysis, label_for_tag
from app.services.exam_service import compute_transfer_comparison
from app.core.crypto import decrypt_text_master
from app.models import ExamResult, LearningProfile, LearningRecord, LearningUnit, User
from app.services.crypto_json import decrypt_json
from app.services.profile_service import child_user_ids, get_profile_for_actor
from app.services.unit_service import UnitError

REVIEW_INTERVAL_DAYS = 7


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _exam_grade_display(exam: ExamResult) -> str | None:
    if exam.grade_label_encrypted:
        return decrypt_text_master(exam.grade_label_encrypted)
    if exam.score is not None and exam.max_score is not None:
        return f"{exam.score}/{exam.max_score}"
    if exam.score is not None:
        return f"{exam.score} Pkt."
    return None


def _unit_title(db: Session, unit_id: uuid.UUID | None) -> str | None:
    if not unit_id:
        return None
    unit = db.get(LearningUnit, unit_id)
    if not unit:
        return None
    return decrypt_text_master(unit.title_encrypted)


def exam_insights_for_profile(db: Session, tenant_id: uuid.UUID, profile_id: uuid.UUID) -> dict:
    exams = (
        db.query(ExamResult)
        .filter(ExamResult.tenant_id == tenant_id, ExamResult.profile_id == profile_id)
        .order_by(ExamResult.taken_at.desc().nullslast(), ExamResult.created_at.desc())
        .all()
    )

    timeline: list[dict] = []
    tag_meta: dict[str, dict] = defaultdict(lambda: {"count": 0, "exam_ids": set()})
    pending_remediation = 0

    for exam in exams:
        title = _unit_title(db, exam.unit_id)
        analysis = None
        if exam.analysis_encrypted:
            raw = decrypt_json(exam.analysis_encrypted)
            if isinstance(raw, dict):
                analysis = raw
        grade = _exam_grade_display(exam)
        taken = exam.taken_at.isoformat() if exam.taken_at else exam.created_at.isoformat()
        transfer = compute_transfer_comparison(
            db, unit_id=exam.unit_id, score=exam.score, max_score=exam.max_score
        )
        timeline.append(
            {
                "exam_id": str(exam.id),
                "unit_id": str(exam.unit_id) if exam.unit_id else None,
                "unit_title": title,
                "taken_at": taken,
                "grade_label": grade,
                "score": exam.score,
                "max_score": exam.max_score,
                "has_analysis": bool(analysis),
                "status": exam.status,
                "remediation_unit_id": str(exam.remediation_unit_id) if exam.remediation_unit_id else None,
                "transfer": transfer,
            }
        )
        if analysis and exam.status == "analyzed" and not exam.remediation_unit_id:
            pending_remediation += 1
        if analysis:
            for tag in collect_tags_from_analysis(analysis):
                tag_meta[tag]["count"] += 1
                tag_meta[tag]["exam_ids"].add(str(exam.id))

    error_tags = [
        {
            "tag": tag,
            "label": label_for_tag(tag),
            "count": meta["count"],
            "exam_count": len(meta["exam_ids"]),
        }
        for tag, meta in sorted(tag_meta.items(), key=lambda x: (-x[1]["count"], x[0]))
    ]

    records = (
        db.query(LearningRecord)
        .filter(LearningRecord.tenant_id == tenant_id, LearningRecord.profile_id == profile_id)
        .order_by(LearningRecord.last_activity_at.desc())
        .all()
    )
    now = datetime.now(timezone.utc)
    review_due: list[dict] = []
    for rec in records:
        stats = decrypt_json(rec.stats_encrypted) or {}
        learn = stats.get("learn") if isinstance(stats.get("learn"), dict) else {}
        if learn.get("status") != "completed":
            continue
        completed_at = _parse_iso(learn.get("completed_at"))
        if not completed_at:
            continue
        if completed_at.tzinfo is None:
            completed_at = completed_at.replace(tzinfo=timezone.utc)
        days = (now - completed_at).days
        if days < REVIEW_INTERVAL_DAYS:
            continue
        review_due.append(
            {
                "record_id": str(rec.id),
                "unit_id": str(rec.unit_id) if rec.unit_id else None,
                "title": decrypt_text_master(rec.title_encrypted),
                "completed_at": completed_at.isoformat(),
                "days_since": days,
            }
        )

    return {
        "exam_count": len(exams),
        "analyzed_count": sum(1 for e in exams if e.analysis_encrypted),
        "pending_remediation": pending_remediation,
        "timeline": timeline[:12],
        "error_tags": error_tags[:20],
        "review_due": review_due[:10],
    }


def child_report_markdown(
    db: Session,
    user: User,
    profile_id: uuid.UUID,
) -> str:
    profile = get_profile_for_actor(db, user, profile_id)
    insights = exam_insights_for_profile(db, user.tenant_id, profile.id)
    lines = [
        f"# Lernbericht — {profile.display_name}",
        "",
        f"Erstellt: {datetime.now(timezone.utc).strftime('%d.%m.%Y')}",
        "",
        "## Schulprüfungen",
    ]
    if not insights["timeline"]:
        lines.append("Noch keine Prüfungen erfasst.")
    else:
        for row in insights["timeline"]:
            date = (row["taken_at"] or "")[:10]
            grade = row["grade_label"] or "—"
            title = row["unit_title"] or "Ohne Einheit"
            status = "analysiert" if row["has_analysis"] else "ohne Analyse"
            lines.append(f"- {date}: **{title}** — {grade} ({status})")
    lines.extend(["", "## Häufige Fehlermuster"])
    if not insights["error_tags"]:
        lines.append("Keine Fehlermuster aus Analysen.")
    else:
        for row in insights["error_tags"]:
            lines.append(f"- {row['label']} ({row['tag']}): {row['count']}× in {row['exam_count']} Prüfung(en)")
    lines.extend(["", "## Wiederholung empfohlen"])
    if not insights["review_due"]:
        lines.append("Keine fälligen Wiederholungen (Schwelle: 7 Tage nach Abschluss).")
    else:
        for row in insights["review_due"]:
            lines.append(
                f"- **{row['title']}** — vor {row['days_since']} Tagen abgeschlossen"
                + (f" (Einheit {row['unit_id']})" if row["unit_id"] else "")
            )
    if insights["pending_remediation"]:
        lines.extend(
            [
                "",
                "## Offene Nacharbeit",
                f"{insights['pending_remediation']} analysierte Prüfung(en) ohne erstellte Nacharbeit-Einheit.",
            ]
        )
    lines.append("")
    lines.append("— LearnAI Elternbericht")
    return "\n".join(lines)


def parent_exam_insights(db: Session, user: User) -> dict:
    if user.is_child:
        raise UnitError("Nur für Eltern-Accounts", "forbidden")
    child_ids = child_user_ids(db, user)
    children_out: list[dict] = []
    for child_id in child_ids:
        child = (
            db.query(User)
            .options(joinedload(User.profile))
            .filter(User.id == child_id, User.tenant_id == user.tenant_id)
            .first()
        )
        if not child or not child.is_active:
            continue
        profile_id = child.profile_id
        if not profile_id:
            continue
        profile = db.get(LearningProfile, profile_id)
        if not profile:
            continue
        insights = exam_insights_for_profile(db, user.tenant_id, profile_id)
        children_out.append(
            {
                "user_id": str(child.id),
                "profile_id": str(profile_id),
                "display_name": profile.display_name,
                **insights,
            }
        )
    return {"children": children_out}
