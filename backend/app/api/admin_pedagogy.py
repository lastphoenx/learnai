"""Admin-API für Pedagogy Golden-Set (nur Lesen + Suite ausführen)."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.auth.dependencies import require_admin
from app.models import User
from app.services.pedagogy_golden_service import get_pedagogy_golden_status, run_pedagogy_golden_suite

router = APIRouter(prefix="/admin/pedagogy-golden", tags=["admin"])


@router.get("")
def admin_pedagogy_golden_status(_admin: User = Depends(require_admin)):
    return get_pedagogy_golden_status()


@router.post("/run")
def admin_run_pedagogy_golden(_admin: User = Depends(require_admin)):
    return run_pedagogy_golden_suite()
