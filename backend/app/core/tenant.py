"""Mandanten-Hilfsfunktionen."""

import uuid

from sqlalchemy.orm import Session

from app.config import settings
from app.models import Tenant

DEFAULT_TENANT_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


def get_default_tenant(db: Session) -> Tenant:
    tenant = db.get(Tenant, DEFAULT_TENANT_ID)
    if tenant:
        return tenant
    tenant = db.query(Tenant).filter(Tenant.slug == settings.default_tenant_slug).first()
    if not tenant:
        raise RuntimeError("Default-Tenant fehlt – alembic upgrade head ausführen")
    return tenant
