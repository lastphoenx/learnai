"""SQLAlchemy-Modelle."""

import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    LargeBinary,
    SmallInteger,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db.session import Base
from app.core.crypto.classification import DataClassification


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class Tenant(Base, TimestampMixin):
    """Mandant – vorbereitet für späteres SaaS."""

    __tablename__ = "tenants"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    slug: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    classification: Mapped[int] = mapped_column(
        SmallInteger, default=DataClassification.INTERNAL, nullable=False
    )

    users: Mapped[list["User"]] = relationship(back_populates="tenant")
    projects: Mapped[list["Project"]] = relationship(back_populates="tenant")
    learning_units: Mapped[list["LearningUnit"]] = relationship(back_populates="tenant")
    learning_records: Mapped[list["LearningRecord"]] = relationship(back_populates="tenant")


class User(Base, TimestampMixin):
    __tablename__ = "users"
    __table_args__ = (Index("ix_users_email_hash_tenant", "tenant_id", "email_hash", unique=True),)

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    email_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    encryption_salt: Mapped[bytes] = mapped_column(LargeBinary(32), nullable=False)
    encrypted_profile: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    totp_secret_encrypted: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    totp_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    totp_required: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    settings_encrypted: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    profile_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("learning_profiles.id", use_alter=True), nullable=True
    )
    is_child: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    classification: Mapped[int] = mapped_column(
        SmallInteger, default=DataClassification.SECRET, nullable=False
    )

    tenant: Mapped["Tenant"] = relationship(back_populates="users")
    sessions: Mapped[list["UserSession"]] = relationship(back_populates="user")
    recovery_codes: Mapped[list["RecoveryCode"]] = relationship(back_populates="user")
    learning_records: Mapped[list["LearningRecord"]] = relationship(back_populates="user")
    profile: Mapped["LearningProfile | None"] = relationship(
        foreign_keys=[profile_id], back_populates="account"
    )
    children: Mapped[list["User"]] = relationship(
        foreign_keys=[parent_id], back_populates="parent"
    )
    parent: Mapped["User | None"] = relationship(
        foreign_keys=[parent_id], remote_side=[id], back_populates="children"
    )
    guardian_of: Mapped[list["ChildGuardian"]] = relationship(
        foreign_keys="ChildGuardian.parent_user_id",
        back_populates="parent",
        cascade="all, delete-orphan",
    )
    guarded_by: Mapped[list["ChildGuardian"]] = relationship(
        foreign_keys="ChildGuardian.child_user_id",
        back_populates="child",
        cascade="all, delete-orphan",
    )


class ChildGuardian(Base):
    """Zuordnung Eltern ↔ Kind (max. 2 Eltern pro Kind)."""

    __tablename__ = "child_guardians"
    __table_args__ = (
        Index("ix_child_guardians_parent_child", "parent_user_id", "child_user_id", unique=True),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    parent_user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    child_user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    parent: Mapped["User"] = relationship(
        foreign_keys=[parent_user_id], back_populates="guardian_of"
    )
    child: Mapped["User"] = relationship(
        foreign_keys=[child_user_id], back_populates="guarded_by"
    )


class UserSession(Base, TimestampMixin):
    __tablename__ = "sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped["User"] = relationship(back_populates="sessions")


class RecoveryCode(Base):
    __tablename__ = "recovery_codes"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    code_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped["User"] = relationship(back_populates="recovery_codes")


class LearningProfile(Base, TimestampMixin):
    """Lerner-Profil: KI-Einstellungen und Lerner-Anzeigename."""

    __tablename__ = "learning_profiles"
    __table_args__ = (Index("ix_learning_profiles_tenant", "tenant_id"),)

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    display_name: Mapped[str] = mapped_column(String(80), nullable=False)
    settings_encrypted: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    managed_by_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    is_child_profile: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    account: Mapped["User | None"] = relationship(
        foreign_keys="User.profile_id", back_populates="profile"
    )


class LoginChallenge(Base):
    __tablename__ = "login_challenges"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class Project(Base, TimestampMixin):
    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    created_by_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    name_encrypted: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    description_encrypted: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    classification: Mapped[int] = mapped_column(
        SmallInteger, default=DataClassification.INTERNAL, nullable=False
    )
    version: Mapped[int] = mapped_column(BigInteger, default=1, nullable=False)
    locked_by_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    tenant: Mapped["Tenant"] = relationship(back_populates="projects")
    tasks: Mapped[list["Task"]] = relationship(back_populates="project")
    members: Mapped[list["ProjectMember"]] = relationship(back_populates="project")


class ProjectMember(Base, TimestampMixin):
    __tablename__ = "project_members"
    __table_args__ = (
        Index("ix_project_members_project_user", "project_id", "user_id", unique=True),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[int] = mapped_column(SmallInteger, nullable=False)

    project: Mapped["Project"] = relationship(back_populates="members")


class Task(Base, TimestampMixin):
    __tablename__ = "tasks"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    title_encrypted: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    body_encrypted: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    status: Mapped[int] = mapped_column(SmallInteger, default=0, nullable=False)
    classification: Mapped[int] = mapped_column(
        SmallInteger, default=DataClassification.INTERNAL, nullable=False
    )
    version: Mapped[int] = mapped_column(BigInteger, default=1, nullable=False)
    locked_by_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    project: Mapped["Project"] = relationship(back_populates="tasks")


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    actor_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(64), nullable=False)
    resource_id: Mapped[uuid.UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    classification: Mapped[int] = mapped_column(
        SmallInteger, default=DataClassification.INTERNAL, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class LearningUnit(Base, TimestampMixin):
    """Lebendes Lerngefäss – Inhalt und Medien sind löschbar."""

    __tablename__ = "learning_units"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    created_by_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    learner_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    profile_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("learning_profiles.id"), nullable=True
    )
    title_encrypted: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    brief_encrypted: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    subject: Mapped[str | None] = mapped_column(String(64), nullable=True)
    language: Mapped[str] = mapped_column(String(8), default="de", nullable=False)
    target_age: Mapped[str | None] = mapped_column(String(32), nullable=True)
    difficulty: Mapped[int] = mapped_column(SmallInteger, default=1, nullable=False)
    task_type: Mapped[str] = mapped_column(String(32), default="mixed", nullable=False)
    status: Mapped[str] = mapped_column(String(24), default="draft", nullable=False)
    auto_purge_sources: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    classification: Mapped[int] = mapped_column(
        SmallInteger, default=DataClassification.INTERNAL, nullable=False
    )

    tenant: Mapped["Tenant"] = relationship(back_populates="learning_units")
    profile: Mapped["LearningProfile | None"] = relationship(foreign_keys=[profile_id])
    modules: Mapped[list["UnitModule"]] = relationship(
        back_populates="unit", cascade="all, delete-orphan"
    )
    sources: Mapped[list["UnitSource"]] = relationship(
        back_populates="unit", cascade="all, delete-orphan"
    )
    exam_results: Mapped[list["ExamResult"]] = relationship(
        back_populates="unit",
        foreign_keys="ExamResult.unit_id",
    )
    remediation_exams: Mapped[list["ExamResult"]] = relationship(
        back_populates="remediation_unit",
        foreign_keys="ExamResult.remediation_unit_id",
    )


class UnitModule(Base, TimestampMixin):
    __tablename__ = "unit_modules"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    unit_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("learning_units.id", ondelete="CASCADE"), nullable=False
    )
    order_index: Mapped[int] = mapped_column(SmallInteger, default=0, nullable=False)
    title_encrypted: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    content_encrypted: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    quiz_encrypted: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)

    unit: Mapped["LearningUnit"] = relationship(back_populates="modules")


class UnitSource(Base, TimestampMixin):
    __tablename__ = "unit_sources"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    unit_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("learning_units.id", ondelete="CASCADE"), nullable=False
    )
    kind: Mapped[str] = mapped_column(String(24), nullable=False)
    original_name_encrypted: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    storage_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    content_type: Mapped[str | None] = mapped_column(String(128), nullable=True)
    byte_size: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    extracted_text_encrypted: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    analysis_encrypted: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    purged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    unit: Mapped["LearningUnit"] = relationship(back_populates="sources")


class LearningRecord(Base, TimestampMixin):
    """Verlauf – überlebt das Löschen der Lerneinheit."""

    __tablename__ = "learning_records"
    __table_args__ = (Index("ix_learning_records_user", "tenant_id", "user_id"),)

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    profile_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("learning_profiles.id"), nullable=True
    )
    unit_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("learning_units.id", ondelete="SET NULL"),
        nullable=True,
    )
    title_encrypted: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    summary_encrypted: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    subject: Mapped[str | None] = mapped_column(String(64), nullable=True)
    language: Mapped[str] = mapped_column(String(8), default="de", nullable=False)
    difficulty: Mapped[int] = mapped_column(SmallInteger, default=1, nullable=False)
    reconstruction_encrypted: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    stats_encrypted: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    last_activity_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    tenant: Mapped["Tenant"] = relationship(back_populates="learning_records")
    user: Mapped["User"] = relationship(back_populates="learning_records")
    profile: Mapped["LearningProfile | None"] = relationship(foreign_keys=[profile_id])
    events: Mapped[list["LearningEvent"]] = relationship(
        back_populates="record", cascade="all, delete-orphan"
    )
    exam_results: Mapped[list["ExamResult"]] = relationship(
        back_populates="record", cascade="all, delete-orphan"
    )


class ExamResult(Base, TimestampMixin):
    """Hochgeladene Schulprüfung (korrigiert) — Phase A: Speichern + Note, ohne KI-Analyse."""

    __tablename__ = "exam_results"
    __table_args__ = (Index("ix_exam_results_record", "record_id"),)

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    record_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("learning_records.id", ondelete="CASCADE"),
        nullable=False,
    )
    unit_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("learning_units.id", ondelete="SET NULL"),
        nullable=True,
    )
    profile_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("learning_profiles.id"), nullable=True
    )
    uploaded_by_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    taken_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    exam_type: Mapped[str] = mapped_column(String(32), default="klassenarbeit", nullable=False)
    grade_label_encrypted: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    score: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    max_score: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    notes_encrypted: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    original_name_encrypted: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    storage_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    content_type: Mapped[str | None] = mapped_column(String(128), nullable=True)
    byte_size: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(24), default="uploaded", nullable=False)
    analysis_encrypted: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    remediation_unit_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("learning_units.id", ondelete="SET NULL"),
        nullable=True,
    )
    classification: Mapped[int] = mapped_column(
        SmallInteger, default=DataClassification.CONFIDENTIAL, nullable=False
    )

    record: Mapped["LearningRecord"] = relationship(back_populates="exam_results")
    unit: Mapped["LearningUnit | None"] = relationship(
        back_populates="exam_results",
        foreign_keys=[unit_id],
    )
    remediation_unit: Mapped["LearningUnit | None"] = relationship(
        back_populates="remediation_exams",
        foreign_keys=[remediation_unit_id],
    )


class LearningEvent(Base):
    __tablename__ = "learning_events"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    record_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("learning_records.id", ondelete="CASCADE"), nullable=False
    )
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    payload_encrypted: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    record: Mapped["LearningRecord"] = relationship(back_populates="events")
