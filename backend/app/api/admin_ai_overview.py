"""Admin: KI-Übersicht aller Lerneinheiten."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.auth.dependencies import require_admin
from app.core.db import get_db
from app.models import User
from app.services.admin_ai_overview_service import build_admin_ai_overview

router = APIRouter(prefix="/admin/ai-overview", tags=["admin"])


@router.get("")
def admin_ai_overview(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    return build_admin_ai_overview(db, admin)
