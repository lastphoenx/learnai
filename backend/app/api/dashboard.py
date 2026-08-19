from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.auth.dependencies import get_app_user
from app.core.db import get_db
from app.models import User
from app.services.dashboard_service import parent_dashboard
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
