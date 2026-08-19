"""Audit-Log – append-only Ereignisprotokoll."""

import uuid

from sqlalchemy.orm import Session

from app.core.crypto.classification import DataClassification
from app.models import AuditLog


def log_event(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    actor_id: uuid.UUID | None,
    action: str,
    resource_type: str,
    resource_id: uuid.UUID | None = None,
    detail: str | None = None,
    classification: int = DataClassification.INTERNAL,
) -> None:
    db.add(
        AuditLog(
            tenant_id=tenant_id,
            actor_id=actor_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            detail=detail,
            classification=classification,
        )
    )
