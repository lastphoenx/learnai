"""Task-CRUD mit Locking und RBAC."""

import uuid
from enum import IntEnum

from sqlalchemy.orm import Session

from app.core.auth.rbac import ProjectRole, require_role
from app.core.crypto import decrypt_text_master, encrypt_text_master
from app.core.crypto.classification import DataClassification
from app.core.locking import LockError, acquire_lock, release_lock, require_lock
from app.models import Project, Task, User
from app.services.audit import log_event


class TaskStatus(IntEnum):
    OPEN = 0
    IN_PROGRESS = 1
    DONE = 2


STATUS_LABELS = {TaskStatus.OPEN: "open", TaskStatus.IN_PROGRESS: "in_progress", TaskStatus.DONE: "done"}


class TaskError(Exception):
    def __init__(self, message: str, code: str = "task_error"):
        self.message = message
        self.code = code
        super().__init__(message)


def _status_from_label(label: str | None) -> int:
    if label is None:
        return TaskStatus.OPEN
    rev = {v: k for k, v in STATUS_LABELS.items()}
    key = label.strip().lower()
    if key not in rev:
        raise TaskError(f"Unbekannter Status: {label}")
    return int(rev[key])


def _decrypt_task(task: Task) -> dict:
    return {
        "id": str(task.id),
        "project_id": str(task.project_id),
        "title": decrypt_text_master(task.title_encrypted),
        "body": decrypt_text_master(task.body_encrypted) if task.body_encrypted else None,
        "status": STATUS_LABELS[TaskStatus(task.status)],
        "classification": task.classification,
        "version": task.version,
        "locked_by_id": str(task.locked_by_id) if task.locked_by_id else None,
        "locked_until": task.locked_until.isoformat() if task.locked_until else None,
        "created_at": task.created_at.isoformat(),
        "updated_at": task.updated_at.isoformat(),
    }


def list_tasks(db: Session, project: Project) -> list[dict]:
    tasks = (
        db.query(Task)
        .filter(Task.project_id == project.id)
        .order_by(Task.created_at.desc())
        .all()
    )
    return [_decrypt_task(t) for t in tasks]


def get_task(db: Session, project: Project, task_id: uuid.UUID) -> dict:
    task = db.get(Task, task_id)
    if not task or task.project_id != project.id:
        raise TaskError("Task nicht gefunden", "not_found")
    return _decrypt_task(task)


def create_task(
    db: Session,
    user: User,
    project: Project,
    *,
    title: str,
    body: str | None = None,
    status: str = "open",
    classification: int = DataClassification.INTERNAL,
) -> dict:
    require_role(db, user, project, ProjectRole.MEMBER)
    task = Task(
        project_id=project.id,
        title_encrypted=encrypt_text_master(title),
        body_encrypted=encrypt_text_master(body) if body else None,
        status=_status_from_label(status),
        classification=classification,
    )
    db.add(task)
    db.flush()
    log_event(
        db,
        tenant_id=project.tenant_id,
        actor_id=user.id,
        action="task.create",
        resource_type="task",
        resource_id=task.id,
    )
    return _decrypt_task(task)


def update_task(
    db: Session,
    user: User,
    project: Project,
    task_id: uuid.UUID,
    *,
    title: str | None = None,
    body: str | None = None,
    status: str | None = None,
    version: int,
) -> dict:
    require_role(db, user, project, ProjectRole.MEMBER)
    task = db.get(Task, task_id)
    if not task or task.project_id != project.id:
        raise TaskError("Task nicht gefunden", "not_found")
    if task.version != version:
        raise TaskError("Konflikt – Task wurde zwischenzeitlich geändert", "version_conflict")
    try:
        require_lock(task, user.id)
    except LockError as exc:
        raise TaskError(exc.message, exc.code) from exc

    if title is not None:
        task.title_encrypted = encrypt_text_master(title)
    if body is not None:
        task.body_encrypted = encrypt_text_master(body) if body else None
    if status is not None:
        task.status = _status_from_label(status)
    task.version += 1
    db.flush()
    log_event(
        db,
        tenant_id=project.tenant_id,
        actor_id=user.id,
        action="task.update",
        resource_type="task",
        resource_id=task.id,
    )
    return _decrypt_task(task)


def delete_task(db: Session, user: User, project: Project, task_id: uuid.UUID) -> None:
    require_role(db, user, project, ProjectRole.MANAGER)
    task = db.get(Task, task_id)
    if not task or task.project_id != project.id:
        raise TaskError("Task nicht gefunden", "not_found")
    log_event(
        db,
        tenant_id=project.tenant_id,
        actor_id=user.id,
        action="task.delete",
        resource_type="task",
        resource_id=task.id,
    )
    db.delete(task)


def lock_task(db: Session, user: User, project: Project, task_id: uuid.UUID) -> dict:
    require_role(db, user, project, ProjectRole.MEMBER)
    task = db.get(Task, task_id)
    if not task or task.project_id != project.id:
        raise TaskError("Task nicht gefunden", "not_found")
    try:
        acquire_lock(task, user.id)
    except LockError as exc:
        raise TaskError(exc.message, exc.code) from exc
    db.flush()
    return _decrypt_task(task)


def unlock_task(db: Session, user: User, project: Project, task_id: uuid.UUID) -> dict:
    task = db.get(Task, task_id)
    if not task or task.project_id != project.id:
        raise TaskError("Task nicht gefunden", "not_found")
    release_lock(task, user.id)
    db.flush()
    return _decrypt_task(task)
