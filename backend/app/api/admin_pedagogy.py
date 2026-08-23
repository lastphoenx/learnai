"""Admin-API für Pedagogy Golden-Set."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.core.auth.dependencies import require_admin
from app.models import User
from app.services.pedagogy_golden_service import (
    PedagogyGoldenError,
    delete_pedagogy_golden_fixture,
    get_pedagogy_golden_fixture,
    list_pedagogy_golden_fixtures,
    run_pedagogy_golden_suite,
    save_pedagogy_golden_fixture,
)

router = APIRouter(prefix="/admin/pedagogy-golden", tags=["admin"])


def _http(exc: PedagogyGoldenError) -> HTTPException:
    mapping = {
        "not_found": status.HTTP_404_NOT_FOUND,
        "invalid_name": status.HTTP_400_BAD_REQUEST,
        "validation_failed": status.HTTP_400_BAD_REQUEST,
        "invalid": status.HTTP_400_BAD_REQUEST,
    }
    return HTTPException(status_code=mapping.get(exc.code, 400), detail=exc.message)


class PedagogyGoldenSaveRequest(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    content: dict
    min_method_labels: int = Field(default=2, ge=1, le=20)
    subject_hint: str | None = Field(default=None, max_length=64)


@router.get("")
def admin_list_pedagogy_golden(_admin: User = Depends(require_admin)):
    return {"fixtures": list_pedagogy_golden_fixtures()}


@router.post("/run")
def admin_run_pedagogy_golden(_admin: User = Depends(require_admin)):
    return run_pedagogy_golden_suite()


@router.get("/{name}")
def admin_get_pedagogy_golden(name: str, _admin: User = Depends(require_admin)):
    try:
        return get_pedagogy_golden_fixture(name)
    except PedagogyGoldenError as exc:
        raise _http(exc) from exc


@router.put("/{name}")
def admin_save_pedagogy_golden(
    name: str,
    body: PedagogyGoldenSaveRequest,
    _admin: User = Depends(require_admin),
):
    try:
        return save_pedagogy_golden_fixture(
            name or body.name,
            body.content,
            min_method_labels=body.min_method_labels,
            subject_hint=body.subject_hint,
        )
    except PedagogyGoldenError as exc:
        raise _http(exc) from exc


@router.delete("/{name}", status_code=status.HTTP_204_NO_CONTENT)
def admin_delete_pedagogy_golden(name: str, _admin: User = Depends(require_admin)):
    try:
        delete_pedagogy_golden_fixture(name)
    except PedagogyGoldenError as exc:
        raise _http(exc) from exc
