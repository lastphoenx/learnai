"""Eltern-Dashboard: Lernstatistik pro Kind."""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session, joinedload

from app.core.crypto import decrypt_text_master
from app.models import LearningRecord, LearningUnit, User
from app.services.crypto_json import decrypt_json
from app.services.profile_service import child_user_ids
from app.services.unit_service import UnitError
from app.services.user_service import user_public_dict


def _learn_from_stats(stats_raw: dict | None) -> dict:
    if not isinstance(stats_raw, dict):
        return {}
    learn = stats_raw.get("learn")
    return learn if isinstance(learn, dict) else {}


def parent_dashboard(db: Session, user: User) -> dict:
    if user.is_child:
        raise UnitError("Nur für Eltern-Accounts", "forbidden")

    child_ids = child_user_ids(db, user)
    children_out: list[dict] = []

    for child_id in child_ids:
        child = (
            db.query(User)
            .options(joinedload(User.profile), joinedload(User.guarded_by))
            .filter(User.id == child_id, User.tenant_id == user.tenant_id)
            .first()
        )
        if not child or not child.is_active:
            continue

        records = (
            db.query(LearningRecord)
            .options(joinedload(LearningRecord.profile))
            .filter(LearningRecord.user_id == child.id, LearningRecord.tenant_id == user.tenant_id)
            .order_by(LearningRecord.last_activity_at.desc())
            .all()
        )

        active_units = (
            db.query(LearningUnit)
            .filter(
                LearningUnit.learner_id == child.id,
                LearningUnit.tenant_id == user.tenant_id,
            )
            .count()
        )

        completed = 0
        in_progress = 0
        quiz_correct = 0
        quiz_total = 0
        recent: list[dict] = []

        for rec in records:
            stats = decrypt_json(rec.stats_encrypted) or {}
            learn = _learn_from_stats(stats)
            status = learn.get("status") or "not_started"
            if status == "completed":
                completed += 1
            elif status == "in_progress":
                in_progress += 1
            quiz_correct += int(learn.get("quiz_correct") or 0)
            quiz_total += int(learn.get("quiz_total") or 0)
            if len(recent) < 5:
                recent.append(
                    {
                        "record_id": str(rec.id),
                        "unit_id": str(rec.unit_id) if rec.unit_id else None,
                        "title": decrypt_text_master(rec.title_encrypted),
                        "status": status,
                        "quiz_correct": learn.get("quiz_correct", 0),
                        "quiz_total": learn.get("quiz_total", 0),
                        "last_activity_at": rec.last_activity_at.isoformat(),
                    }
                )

        pub = user_public_dict(child)
        children_out.append(
            {
                "user_id": str(child.id),
                "display_name": pub.get("display_name") or pub.get("learner_name") or "Kind",
                "profile_id": pub.get("profile_id"),
                "active_units": active_units,
                "records_total": len(records),
                "completed": completed,
                "in_progress": in_progress,
                "quiz_correct": quiz_correct,
                "quiz_total": quiz_total,
                "quiz_percent": round(100 * quiz_correct / quiz_total) if quiz_total else None,
                "recent": recent,
            }
        )

    return {"children": children_out, "child_count": len(children_out)}
