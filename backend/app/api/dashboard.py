from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse, Response
from sqlalchemy.orm import Session
from uuid import UUID

from app.core.auth.dependencies import get_app_user
from app.core.db import get_db
from app.models import User
from app.services.dashboard_service import parent_dashboard
from app.services.exam_insights_service import child_report_markdown, parent_exam_insights
from app.services.pdf_export_service import child_report_pdf
from app.services.profile_service import ProfileError
from app.services.unit_service import UnitError

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


def _http(exc: UnitError) -> HTTPException:
    mapping = {"forbidden": 403}
    return HTTPException(status_code=mapping.get(exc.code, 400), detail=exc.message)


@router.get("/parent")
def dashboard_parent(user: User = Depends(get_app_user), db: Session = Depends(get_db)):
    try:
        return parent_dashboard(db, user)
    except UnitError as exc:
        raise _http(exc) from exc


@router.get("/parent/exam-insights")
def dashboard_exam_insights(user: User = Depends(get_app_user), db: Session = Depends(get_db)):
    try:
        return parent_exam_insights(db, user)
    except UnitError as exc:
        raise _http(exc) from exc


@router.get("/parent/report/{profile_id}")
def dashboard_child_report(
    profile_id: UUID,
    user: User = Depends(get_app_user),
    db: Session = Depends(get_db),
):
    try:
        text = child_report_markdown(db, user, profile_id)
        filename = f"learnai-bericht-{profile_id}.md"
        return PlainTextResponse(
            content=text,
            media_type="text/markdown; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except ProfileError as exc:
        code = 403 if exc.code == "forbidden" else 404
        raise HTTPException(status_code=code, detail=exc.message) from exc
    except UnitError as exc:
        raise _http(exc) from exc


@router.get("/parent/report/{profile_id}/pdf")
def dashboard_child_report_pdf(
    profile_id: UUID,
    user: User = Depends(get_app_user),
    db: Session = Depends(get_db),
):
    try:
        pdf_bytes, filename = child_report_pdf(db, user, profile_id)
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except ProfileError as exc:
        code = 403 if exc.code == "forbidden" else 404
        raise HTTPException(status_code=code, detail=exc.message) from exc
    except UnitError as exc:
        raise _http(exc) from exc
