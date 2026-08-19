"""Projekt-CRUD mit RBAC, Locking und Verschlüsselung."""

import uuid

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.auth.rbac import ProjectRole, get_user_project_role, require_role
from app.core.crypto import decrypt_text_master, encrypt_text_master
from app.core.crypto.classification import DataClassification
from app.core.locking import LockError, acquire_lock, release_lock, require_lock
from app.models import Project, ProjectMember, User
from app.services.audit import log_event
from app.services.member_service import add_project_owner


class ProjectError(Exception):
    def __init__(self, message: str, code: str = "project_error"):
        self.message = message
        self.code = code
        super().__init__(message)


def _decrypt_project(project: Project) -> dict:
    return {
        "id": str(project.id),
        "name": decrypt_text_master(project.name_encrypted),
        "description": (
            decrypt_text_master(project.description_encrypted)
            if project.description_encrypted
            else None
        ),
        "classification": project.classification,
        "version": project.version,
        "locked_by_id": str(project.locked_by_id) if project.locked_by_id else None,
        "locked_until": project.locked_until.isoformat() if project.locked_until else None,
        "created_at": project.created_at.isoformat(),
        "updated_at": project.updated_at.isoformat(),
    }


def _accessible_projects_query(db: Session, user: User):
    if user.is_admin:
        return db.query(Project).filter(Project.tenant_id == user.tenant_id)
    member_project_ids = (
        db.query(ProjectMember.project_id).filter(ProjectMember.user_id == user.id).subquery()
    )
    return db.query(Project).filter(
        Project.tenant_id == user.tenant_id,
        or_(Project.created_by_id == user.id, Project.id.in_(member_project_ids)),
    )


def list_projects(db: Session, user: User) -> list[dict]:
    projects = _accessible_projects_query(db, user).order_by(Project.created_at.desc()).all()
    return [_decrypt_project(p) for p in projects]


def get_project_for_user(db: Session, user: User, project_id: uuid.UUID) -> dict:
    project = db.get(Project, project_id)
    if not project or project.tenant_id != user.tenant_id:
        raise ProjectError("Projekt nicht gefunden", "not_found")
    if get_user_project_role(db, user, project) is None:
        raise ProjectError("Kein Zugriff auf dieses Projekt", "forbidden")
    return _decrypt_project(project)


def create_project(
    db: Session,
    user: User,
    *,
    name: str,
    description: str | None = None,
    classification: int = DataClassification.INTERNAL,
) -> dict:
    project = Project(
        tenant_id=user.tenant_id,
        created_by_id=user.id,
        name_encrypted=encrypt_text_master(name),
        description_encrypted=encrypt_text_master(description) if description else None,
        classification=classification,
    )
    db.add(project)
    db.flush()
    add_project_owner(db, project, user)
    log_event(
        db,
        tenant_id=user.tenant_id,
        actor_id=user.id,
        action="project.create",
        resource_type="project",
        resource_id=project.id,
    )
    return _decrypt_project(project)


def update_project(
    db: Session,
    user: User,
    project_id: uuid.UUID,
    *,
    name: str | None = None,
    description: str | None = None,
    version: int,
) -> dict:
    project = db.get(Project, project_id)
    if not project or project.tenant_id != user.tenant_id:
        raise ProjectError("Projekt nicht gefunden", "not_found")
    require_role(db, user, project, ProjectRole.MANAGER)
    if project.version != version:
        raise ProjectError("Konflikt – Datensatz wurde zwischenzeitlich geändert", "version_conflict")
    try:
        require_lock(project, user.id)
    except LockError as exc:
        raise ProjectError(exc.message, exc.code) from exc

    if name is not None:
        project.name_encrypted = encrypt_text_master(name)
    if description is not None:
        project.description_encrypted = encrypt_text_master(description) if description else None
    project.version += 1
    db.flush()
    log_event(
        db,
        tenant_id=user.tenant_id,
        actor_id=user.id,
        action="project.update",
        resource_type="project",
        resource_id=project.id,
    )
    return _decrypt_project(project)


def delete_project(db: Session, user: User, project_id: uuid.UUID) -> None:
    project = db.get(Project, project_id)
    if not project or project.tenant_id != user.tenant_id:
        raise ProjectError("Projekt nicht gefunden", "not_found")
    require_role(db, user, project, ProjectRole.OWNER)
    log_event(
        db,
        tenant_id=user.tenant_id,
        actor_id=user.id,
        action="project.delete",
        resource_type="project",
        resource_id=project.id,
    )
    db.delete(project)


def lock_project(db: Session, user: User, project_id: uuid.UUID) -> dict:
    project = db.get(Project, project_id)
    if not project or project.tenant_id != user.tenant_id:
        raise ProjectError("Projekt nicht gefunden", "not_found")
    require_role(db, user, project, ProjectRole.MANAGER)
    try:
        acquire_lock(project, user.id)
    except LockError as exc:
        raise ProjectError(exc.message, exc.code) from exc
    db.flush()
    return _decrypt_project(project)


def unlock_project(db: Session, user: User, project_id: uuid.UUID) -> dict:
    project = db.get(Project, project_id)
    if not project or project.tenant_id != user.tenant_id:
        raise ProjectError("Projekt nicht gefunden", "not_found")
    release_lock(project, user.id)
    db.flush()
    return _decrypt_project(project)
