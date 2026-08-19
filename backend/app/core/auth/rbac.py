"""Rollenbasierte Zugriffskontrolle auf Projektebene."""

from enum import IntEnum
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models import Project, ProjectMember, User


class ProjectRole(IntEnum):
    VIEWER = 1
    MEMBER = 2
    MANAGER = 3
    OWNER = 4


ROLE_LABELS = {
    ProjectRole.VIEWER: "viewer",
    ProjectRole.MEMBER: "member",
    ProjectRole.MANAGER: "manager",
    ProjectRole.OWNER: "owner",
}


def role_from_label(label: str) -> ProjectRole:
    mapping = {v: k for k, v in ROLE_LABELS.items()}
    key = label.strip().lower()
    if key not in mapping:
        raise ValueError(f"Unbekannte Rolle: {label}")
    return mapping[key]


def get_user_project_role(db: Session, user: User, project: Project) -> ProjectRole | None:
    if user.is_admin and user.tenant_id == project.tenant_id:
        return ProjectRole.OWNER
    if project.created_by_id == user.id:
        return ProjectRole.OWNER
    member = (
        db.query(ProjectMember)
        .filter(ProjectMember.project_id == project.id, ProjectMember.user_id == user.id)
        .first()
    )
    if member:
        return ProjectRole(member.role)
    return None


def require_role(
    db: Session,
    user: User,
    project: Project,
    minimum: ProjectRole,
) -> ProjectRole:
    role = get_user_project_role(db, user, project)
    if role is None or role < minimum:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Keine Berechtigung für diese Aktion",
        )
    return role


def get_accessible_project(
    db: Session,
    user: User,
    project_id: UUID,
) -> Project:
    project = db.get(Project, project_id)
    if not project or project.tenant_id != user.tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Projekt nicht gefunden")
    if get_user_project_role(db, user, project) is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Kein Zugriff auf dieses Projekt")
    return project
