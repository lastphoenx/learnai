from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.core.auth.dependencies import get_app_user
from app.core.db import get_db
from app.models import User
from app.ai.errors import LlmError
from app.ai.generate import generate_modules
from app.schemas import (
    RecordRebuildRequest,
    UnitCreateRequest,
    UnitGenerateRequest,
    UnitUpdateRequest,
)
from app.services.unit_service import UnitError, add_source, create_unit, create_unit_from_record, delete_source, delete_unit, get_record, get_unit, list_records, list_units, purge_source_file_keep_meta, update_unit_flags

router = APIRouter(prefix="/units", tags=["units"])
records_router = APIRouter(prefix="/records", tags=["records"])


def _http(exc: UnitError) -> HTTPException:
    mapping = {
        "not_found": status.HTTP_404_NOT_FOUND,
        "forbidden": status.HTTP_403_FORBIDDEN,
        "invalid_difficulty": status.HTTP_400_BAD_REQUEST,
        "invalid_task_type": status.HTTP_400_BAD_REQUEST,
    }
    return HTTPException(status_code=mapping.get(exc.code, 400), detail=exc.message)


@router.get("")
def units_list(user: User = Depends(get_app_user), db: Session = Depends(get_db)):
    return list_units(db, user)


@router.post("", status_code=status.HTTP_201_CREATED)
def units_create(
    body: UnitCreateRequest,
    user: User = Depends(get_app_user),
    db: Session = Depends(get_db),
):
    try:
        result = create_unit(
            db,
            user,
            title=body.title,
            brief=body.brief,
            subject=body.subject,
            language=body.language,
            target_age=body.target_age,
            difficulty=body.difficulty,
            task_type=body.task_type,
            auto_purge_sources=body.auto_purge_sources,
        )
        db.commit()
        return result
    except UnitError as exc:
        db.rollback()
        raise _http(exc) from exc


@router.get("/{unit_id}")
def units_get(unit_id: UUID, user: User = Depends(get_app_user), db: Session = Depends(get_db)):
    try:
        return get_unit(db, user, unit_id)
    except UnitError as exc:
        raise _http(exc) from exc


@router.post("/{unit_id}/generate")
def units_generate(
    unit_id: UUID,
    body: UnitGenerateRequest,
    user: User = Depends(get_app_user),
    db: Session = Depends(get_db),
):
    try:
        result = generate_modules(db, user, unit_id, provider=body.provider)
        db.commit()
        return result
    except UnitError as exc:
        db.rollback()
        raise _http(exc) from exc
    except LlmError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=exc.message) from exc


@router.patch("/{unit_id}")
def units_patch(
    unit_id: UUID,
    body: UnitUpdateRequest,
    user: User = Depends(get_app_user),
    db: Session = Depends(get_db),
):
    try:
        result = update_unit_flags(db, user, unit_id, auto_purge_sources=body.auto_purge_sources)
        db.commit()
        return result
    except UnitError as exc:
        db.rollback()
        raise _http(exc) from exc


@router.delete("/{unit_id}", status_code=status.HTTP_204_NO_CONTENT)
def units_delete(unit_id: UUID, user: User = Depends(get_app_user), db: Session = Depends(get_db)):
    try:
        delete_unit(db, user, unit_id)
        db.commit()
    except UnitError as exc:
        db.rollback()
        raise _http(exc) from exc


@router.post("/{unit_id}/sources", status_code=status.HTTP_201_CREATED)
async def units_upload_source(
    unit_id: UUID,
    user: User = Depends(get_app_user),
    db: Session = Depends(get_db),
    file: UploadFile = File(...),
):
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Leere Datei")
    if len(data) > 25 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Datei zu gross (max. 25 MB)")
    try:
        result = add_source(
            db,
            user,
            unit_id,
            filename=file.filename or "upload",
            content_type=file.content_type,
            data=data,
        )
        db.commit()
        return result
    except UnitError as exc:
        db.rollback()
        raise _http(exc) from exc


@router.delete("/{unit_id}/sources/{source_id}", status_code=status.HTTP_204_NO_CONTENT)
def units_delete_source(
    unit_id: UUID,
    source_id: UUID,
    user: User = Depends(get_app_user),
    db: Session = Depends(get_db),
):
    try:
        delete_source(db, user, unit_id, source_id)
        db.commit()
    except UnitError as exc:
        db.rollback()
        raise _http(exc) from exc


@router.post("/{unit_id}/sources/{source_id}/purge")
def units_purge_source(
    unit_id: UUID,
    source_id: UUID,
    user: User = Depends(get_app_user),
    db: Session = Depends(get_db),
):
    try:
        result = purge_source_file_keep_meta(db, user, unit_id, source_id)
        db.commit()
        return result
    except UnitError as ext:
        db.rollback()
        raise _http(ext) from ext


@records_router.get("")
def records_list(user: User = Depends(get_app_user), db: Session = Depends(get_db)):
    return list_records(db, user)


@records_router.get("/{record_id}")
def records_get(record_id: UUID, user: User = Depends(get_app_user), db: Session = Depends(get_db)):
    try:
        return get_record(db, user, record_id)
    except UnitError as exc:
        raise _http(exc) from exc


@records_router.post("/{record_id}/rebuild", status_code=status.HTTP_201_CREATED)
def records_rebuild(
    record_id: UUID,
    body: RecordRebuildRequest,
    user: User = Depends(get_app_user),
    db: Session = Depends(get_db),
):
    try:
        result = create_unit_from_record(db, user, record_id, difficulty=body.difficulty)
        db.commit()
        return result
    except UnitError as exc:
        db.rollback()
        raise _http(exc) from exc
