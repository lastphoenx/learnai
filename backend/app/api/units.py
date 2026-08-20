from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse, Response
from sqlalchemy.orm import Session

from app.core.auth.dependencies import get_app_user
from app.core.db import get_db
from app.models import User
from app.ai.errors import LlmError
from app.ai.generate import generate_modules
from app.schemas import (
    LearnAnswerRequest,
    LearnModuleRequest,
    LearnPositionRequest,
    RecordRebuildRequest,
    SourceUrlRequest,
    ExamUpdateRequest,
    ExamAnalysisUpdateRequest,
    UnitAssignRequest,
    UnitCreateRequest,
    UnitGenerateRequest,
    UnitUpdateRequest,
)
from app.services.learn_service import (
    complete_learn,
    get_learn_state,
    mark_text_read,
    reset_learn_progress,
    save_learn_position,
    submit_quiz_answer,
)
from app.services.exam_service import (
    analyze_exam,
    create_exam,
    create_remediation_from_exam,
    delete_exam,
    get_exam_file,
    list_exams_for_record,
    list_exams_for_unit,
    update_exam,
    update_exam_analysis,
)
from app.services.unit_service import UnitError, add_source, add_source_url, assign_unit_to_profiles, create_unit, create_review_from_unit, create_unit_from_record, create_units, delete_source, delete_unit, get_record, get_unit, list_records, list_units, purge_source_file_keep_meta, update_unit, update_unit_flags
from app.services.pdf_export_service import unit_worksheet_pdf
from app.ai.task_types import math_focus_public, task_types_public

router = APIRouter(prefix="/units", tags=["units"])
records_router = APIRouter(prefix="/records", tags=["records"])


def _http(exc: UnitError) -> HTTPException:
    mapping = {
        "not_found": status.HTTP_404_NOT_FOUND,
        "forbidden": status.HTTP_403_FORBIDDEN,
        "invalid_difficulty": status.HTTP_400_BAD_REQUEST,
        "invalid_title": status.HTTP_400_BAD_REQUEST,
        "invalid_task_type": status.HTTP_400_BAD_REQUEST,
        "no_modules": status.HTTP_400_BAD_REQUEST,
        "invalid_index": status.HTTP_400_BAD_REQUEST,
        "invalid_phase": status.HTTP_400_BAD_REQUEST,
        "invalid_question": status.HTTP_400_BAD_REQUEST,
        "bad_url": status.HTTP_400_BAD_REQUEST,
        "invalid_exam_type": status.HTTP_400_BAD_REQUEST,
        "invalid_score": status.HTTP_400_BAD_REQUEST,
        "invalid_profile": status.HTTP_400_BAD_REQUEST,
        "already_assigned": status.HTTP_400_BAD_REQUEST,
        "no_file": status.HTTP_400_BAD_REQUEST,
        "analysis_failed": status.HTTP_400_BAD_REQUEST,
        "not_analyzed": status.HTTP_400_BAD_REQUEST,
    }
    return HTTPException(status_code=mapping.get(exc.code, 400), detail=exc.message)


@router.get("/task-types")
def units_task_types():
    return {"task_types": task_types_public(), "math_focus": math_focus_public()}


@router.post("/{unit_id}/review", status_code=status.HTTP_201_CREATED)
def units_create_review(unit_id: UUID, user: User = Depends(get_app_user), db: Session = Depends(get_db)):
    try:
        result = create_review_from_unit(db, user, unit_id)
        db.commit()
        return result
    except UnitError as exc:
        db.rollback()
        raise _http(exc) from exc


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
        profile_ids = [UUID(x) for x in body.profile_ids] if body.profile_ids else None
        results = create_units(
            db,
            user,
            title=body.title,
            brief=body.brief,
            subject=body.subject,
            language=body.language,
            target_age=body.target_age,
            difficulty=body.difficulty,
            task_type=body.task_type,
            math_focus=body.math_focus,
            auto_purge_sources=body.auto_purge_sources,
            profile_id=UUID(body.profile_id) if body.profile_id else None,
            profile_ids=profile_ids,
        )
        db.commit()
        if len(results) == 1:
            return results[0]
        return {"units": results, "created_count": len(results)}
    except UnitError as exc:
        db.rollback()
        raise _http(exc) from exc


@router.post("/{unit_id}/assign", status_code=status.HTTP_201_CREATED)
def units_assign(
    unit_id: UUID,
    body: UnitAssignRequest,
    user: User = Depends(get_app_user),
    db: Session = Depends(get_db),
):
    try:
        result = assign_unit_to_profiles(
            db,
            user,
            unit_id,
            [UUID(x) for x in body.profile_ids],
        )
        db.commit()
        return {"units": result, "created_count": len(result)}
    except UnitError as exc:
        db.rollback()
        raise _http(exc) from exc


@router.get("/{unit_id}")
def units_get(unit_id: UUID, user: User = Depends(get_app_user), db: Session = Depends(get_db)):
    try:
        return get_unit(db, user, unit_id)
    except UnitError as exc:
        raise _http(exc) from exc


@router.get("/{unit_id}/worksheet.pdf")
def units_worksheet_pdf(
    unit_id: UUID,
    user: User = Depends(get_app_user),
    db: Session = Depends(get_db),
):
    try:
        pdf_bytes, filename = unit_worksheet_pdf(db, user, unit_id)
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
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
        result = update_unit(
            db,
            user,
            unit_id,
            title=body.title,
            brief=body.brief,
            subject=body.subject,
            language=body.language,
            target_age=body.target_age,
            difficulty=body.difficulty,
            task_type=body.task_type,
            math_focus=body.math_focus,
            auto_purge_sources=body.auto_purge_sources,
        )
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


@router.post("/{unit_id}/sources/url", status_code=status.HTTP_201_CREATED)
def units_add_source_url(
    unit_id: UUID,
    body: SourceUrlRequest,
    user: User = Depends(get_app_user),
    db: Session = Depends(get_db),
):
    try:
        result = add_source_url(db, user, unit_id, url=body.url)
        db.commit()
        return result
    except UnitError as exc:
        db.rollback()
        raise _http(exc) from exc


@router.get("/{unit_id}/exams")
def units_list_exams(unit_id: UUID, user: User = Depends(get_app_user), db: Session = Depends(get_db)):
    try:
        return list_exams_for_unit(db, user, unit_id)
    except UnitError as exc:
        raise _http(exc) from exc


@router.post("/{unit_id}/exams", status_code=status.HTTP_201_CREATED)
async def units_upload_exam(
    unit_id: UUID,
    user: User = Depends(get_app_user),
    db: Session = Depends(get_db),
    file: UploadFile = File(...),
    taken_at: str | None = Form(default=None),
    exam_type: str = Form(default="klassenarbeit"),
    grade_label: str | None = Form(default=None),
    score: int | None = Form(default=None),
    max_score: int | None = Form(default=None),
    notes: str | None = Form(default=None),
):
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Leere Datei")
    if len(data) > 25 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Datei zu gross (max. 25 MB)")
    parsed_date = None
    if taken_at and taken_at.strip():
        try:
            from datetime import date as date_cls

            parsed_date = date_cls.fromisoformat(taken_at.strip()[:10])
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Ungültiges Datum (YYYY-MM-DD)") from exc
    try:
        result = create_exam(
            db,
            user,
            unit_id,
            filename=file.filename or "pruefung",
            content_type=file.content_type,
            data=data,
            taken_at=parsed_date,
            exam_type=exam_type,
            grade_label=grade_label,
            score=score,
            max_score=max_score,
            notes=notes,
        )
        db.commit()
        return result
    except UnitError as exc:
        db.rollback()
        raise _http(exc) from exc


@router.patch("/{unit_id}/exams/{exam_id}")
def units_patch_exam(
    unit_id: UUID,
    exam_id: UUID,
    body: ExamUpdateRequest,
    user: User = Depends(get_app_user),
    db: Session = Depends(get_db),
):
    try:
        result = update_exam(
            db,
            user,
            unit_id,
            exam_id,
            taken_at=body.taken_at,
            exam_type=body.exam_type,
            grade_label=body.grade_label,
            score=body.score,
            max_score=body.max_score,
            notes=body.notes,
            clear_grade=body.clear_grade,
            clear_notes=body.clear_notes,
        )
        db.commit()
        return result
    except UnitError as exc:
        db.rollback()
        raise _http(exc) from exc


@router.delete("/{unit_id}/exams/{exam_id}", status_code=status.HTTP_204_NO_CONTENT)
def units_delete_exam(
    unit_id: UUID,
    exam_id: UUID,
    user: User = Depends(get_app_user),
    db: Session = Depends(get_db),
):
    try:
        delete_exam(db, user, unit_id, exam_id)
        db.commit()
    except UnitError as exc:
        db.rollback()
        raise _http(exc) from exc


@router.get("/{unit_id}/exams/{exam_id}/file")
def units_exam_file(
    unit_id: UUID,
    exam_id: UUID,
    user: User = Depends(get_app_user),
    db: Session = Depends(get_db),
):
    try:
        exam, path = get_exam_file(db, user, unit_id, exam_id)
        from app.core.crypto import decrypt_text_master

        name = (
            decrypt_text_master(exam.original_name_encrypted)
            if exam.original_name_encrypted
            else "pruefung"
        )
        return FileResponse(path, media_type=exam.content_type or "application/octet-stream", filename=name)
    except UnitError as exc:
        raise _http(exc) from exc


@router.patch("/{unit_id}/exams/{exam_id}/analysis")
def units_patch_exam_analysis(
    unit_id: UUID,
    exam_id: UUID,
    body: ExamAnalysisUpdateRequest,
    user: User = Depends(get_app_user),
    db: Session = Depends(get_db),
):
    try:
        result = update_exam_analysis(
            db,
            user,
            unit_id,
            exam_id,
            summary=body.summary,
            strengths=body.strengths,
            gaps=body.gaps,
            error_patterns=body.error_patterns,
            tasks=body.tasks,
            recommendations=body.recommendations,
        )
        db.commit()
        return result
    except UnitError as exc:
        db.rollback()
        raise _http(exc) from exc


@router.post("/{unit_id}/exams/{exam_id}/analyze")
def units_analyze_exam(
    unit_id: UUID,
    exam_id: UUID,
    user: User = Depends(get_app_user),
    db: Session = Depends(get_db),
):
    try:
        result = analyze_exam(db, user, unit_id, exam_id)
        db.commit()
        return result
    except UnitError as exc:
        db.rollback()
        raise _http(exc) from exc


@router.post("/{unit_id}/exams/{exam_id}/remediation", status_code=status.HTTP_201_CREATED)
def units_create_remediation(
    unit_id: UUID,
    exam_id: UUID,
    user: User = Depends(get_app_user),
    db: Session = Depends(get_db),
):
    try:
        result = create_remediation_from_exam(db, user, unit_id, exam_id)
        db.commit()
        return result
    except UnitError as exc:
        db.rollback()
        raise _http(exc) from exc


@router.get("/{unit_id}/learn")
def units_learn_get(unit_id: UUID, user: User = Depends(get_app_user), db: Session = Depends(get_db)):
    try:
        result = get_learn_state(db, user, unit_id)
        db.commit()
        return result
    except UnitError as exc:
        db.rollback()
        raise _http(exc) from exc


@router.patch("/{unit_id}/learn/position")
def units_learn_position(
    unit_id: UUID,
    body: LearnPositionRequest,
    user: User = Depends(get_app_user),
    db: Session = Depends(get_db),
):
    try:
        result = save_learn_position(
            db,
            user,
            unit_id,
            module_index=body.module_index,
            phase=body.phase,
            question_index=body.question_index,
        )
        db.commit()
        return result
    except UnitError as exc:
        db.rollback()
        raise _http(exc) from exc


@router.post("/{unit_id}/learn/text-read")
def units_learn_text_read(
    unit_id: UUID,
    body: LearnModuleRequest,
    user: User = Depends(get_app_user),
    db: Session = Depends(get_db),
):
    try:
        result = mark_text_read(db, user, unit_id, UUID(body.module_id))
        db.commit()
        return result
    except UnitError as exc:
        db.rollback()
        raise _http(exc) from exc


@router.post("/{unit_id}/learn/answer")
def units_learn_answer(
    unit_id: UUID,
    body: LearnAnswerRequest,
    user: User = Depends(get_app_user),
    db: Session = Depends(get_db),
):
    try:
        result = submit_quiz_answer(
            db,
            user,
            unit_id,
            UUID(body.module_id),
            body.question_index,
            body.selected,
        )
        db.commit()
        return result
    except UnitError as exc:
        db.rollback()
        raise _http(exc) from exc


@router.post("/{unit_id}/learn/complete")
def units_learn_complete(unit_id: UUID, user: User = Depends(get_app_user), db: Session = Depends(get_db)):
    try:
        result = complete_learn(db, user, unit_id)
        db.commit()
        return result
    except UnitError as exc:
        db.rollback()
        raise _http(exc) from exc


@router.post("/{unit_id}/learn/reset")
def units_learn_reset(unit_id: UUID, user: User = Depends(get_app_user), db: Session = Depends(get_db)):
    try:
        result = reset_learn_progress(db, user, unit_id)
        db.commit()
        return result
    except UnitError as exc:
        db.rollback()
        raise _http(exc) from exc


@records_router.get("")
def records_list(user: User = Depends(get_app_user), db: Session = Depends(get_db)):
    return list_records(db, user)


@records_router.get("/{record_id}")
def records_get(record_id: UUID, user: User = Depends(get_app_user), db: Session = Depends(get_db)):
    try:
        return get_record(db, user, record_id)
    except UnitError as exc:
        raise _http(exc) from exc


@records_router.get("/{record_id}/exams")
def records_list_exams(record_id: UUID, user: User = Depends(get_app_user), db: Session = Depends(get_db)):
    try:
        return list_exams_for_record(db, user, record_id)
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
        result = create_unit_from_record(db, user, record_id, difficulty=body.difficulty, task_type=body.task_type)
        db.commit()
        return result
    except UnitError as exc:
        db.rollback()
        raise _http(exc) from exc
