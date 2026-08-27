"""Admin-API für Task-Type Golden-Set (nur Lesen + Suite ausführen)."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.auth.dependencies import require_admin
from app.models import User
from app.services.task_type_golden_service import get_task_type_golden_status, run_task_type_golden_suite

router = APIRouter(prefix="/admin/task-type-golden", tags=["admin"])


@router.get("")
def admin_task_type_golden_status(_admin: User = Depends(require_admin)):
    return get_task_type_golden_status()


@router.post("/run")
def admin_run_task_type_golden(_admin: User = Depends(require_admin)):
    return run_task_type_golden_suite()
