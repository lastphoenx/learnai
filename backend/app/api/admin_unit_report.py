"""Admin-API: Qualitätsreport per Referenz-Code."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.auth.dependencies import require_admin
from app.core.db import get_db
from app.models import User
from app.services.unit_quality_report_service import build_unit_quality_report_for_user
from app.services.unit_service import UnitError

router = APIRouter(prefix="/admin/unit-report", tags=["admin"])


def _http(exc: UnitError) -> HTTPException:
    mapping = {
        "not_found": status.HTTP_404_NOT_FOUND,
        "invalid": status.HTTP_400_BAD_REQUEST,
        "forbidden": status.HTTP_403_FORBIDDEN,
    }
    return HTTPException(status_code=mapping.get(exc.code, 400), detail=exc.message)


@router.get("")
def admin_unit_quality_report(
    ref: str = Query(..., min_length=4, max_length=16, description="0001 oder 0001.0001"),
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    try:
        result = build_unit_quality_report_for_user(db, admin, ref)
        db.commit()
        return result
    except UnitError as exc:
        db.rollback()
        raise _http(exc) from exc
