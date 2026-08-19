"""Projekt-Mitglieder und Rollen."""

import uuid

from sqlalchemy.orm import Session

from app.core.auth.rbac import ROLE_LABELS, ProjectRole, role_from_label
from app.models import Project, ProjectMember, User
from app.services.audit import log_event


class MemberError(Exception):
    def __init__(self, message: str, code: str = "member_error"):
        self.message = message
        self.code = code
        super().__init__(message)


def add_project_owner(db: Session, project: Project, user: User) -> None:
    db.add(
        ProjectMember(
            project_id=project.id,
            user_id=user.id,
            role=ProjectRole.OWNER,
        )
    )


def list_members(db: Session, project: Project) -> list[dict]:
    rows = db.query(ProjectMember).filter(ProjectMember.project_id == project.id).all()
    return [
        {
            "id": str(m.id),
            "user_id": str(m.user_id),
            "role": ROLE_LABELS[ProjectRole(m.role)],
            "created_at": m.created_at.isoformat(),
        }
        for m in rows
    ]


def add_member(
    db: Session,
    actor: User,
    project: Project,
    *,
    user_id: uuid.UUID,
    role_label: str,
) -> dict:
    role = role_from_label(role_label)
    if role == ProjectRole.OWNER:
        raise MemberError("Owner-Rolle kann nicht zugewiesen werden")
    if db.get(User, user_id) is None:
        raise MemberError("Benutzer nicht gefunden", "user_not_found")
    existing = (
        db.query(ProjectMember)
        .filter(ProjectMember.project_id == project.id, ProjectMember.user_id == user_id)
        .first()
    )
    if existing:
        existing.role = int(role)
        member = existing
    else:
        member = ProjectMember(project_id=project.id, user_id=user_id, role=int(role))
        db.add(member)
    db.flush()
    log_event(
        db,
        tenant_id=project.tenant_id,
        actor_id=actor.id,
        action="project.member.add",
        resource_type="project",
        resource_id=project.id,
        detail=f"user={user_id} role={role_label}",
    )
    return {
        "id": str(member.id),
        "user_id": str(member.user_id),
        "role": ROLE_LABELS[ProjectRole(member.role)],
        "created_at": member.created_at.isoformat(),
    }


def remove_member(
    db: Session,
    actor: User,
    project: Project,
    member_id: uuid.UUID,
) -> None:
    member = db.get(ProjectMember, member_id)
    if not member or member.project_id != project.id:
        raise MemberError("Mitglied nicht gefunden", "not_found")
    if member.role == ProjectRole.OWNER:
        raise MemberError("Owner kann nicht entfernt werden")
    log_event(
        db,
        tenant_id=project.tenant_id,
        actor_id=actor.id,
        action="project.member.remove",
        resource_type="project",
        resource_id=project.id,
        detail=f"user={member.user_id}",
    )
    db.delete(member)
