from datetime import date
from typing import Literal

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=12)
    display_name: str = Field(default="", max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TwoFactorVerifyRequest(BaseModel):
    totp_code: str | None = None
    recovery_code: str | None = None


class TwoFactorSetupRequest(BaseModel):
    email: EmailStr


class TwoFactorConfirmRequest(BaseModel):
    code: str = Field(min_length=6, max_length=8)
    email: EmailStr | None = None


class TwoFactorSetupResponse(BaseModel):
    provisioning_uri: str
    secret: str


class UserResponse(BaseModel):
    id: str
    is_admin: bool
    is_child: bool = False
    parent_id: str | None = None
    parent_ids: list[str] = Field(default_factory=list)
    profile_id: str | None = None
    learner_name: str = ""
    child_count: int = 0
    totp_enabled: bool
    totp_required: bool
    must_enroll_2fa: bool = False
    display_name: str = ""
    llm_provider: str = ""
    llm_model: str = ""
    by_task: dict[str, dict[str, str]] = Field(default_factory=dict)
    ki_summary: str = ""


class ProfileResponse(BaseModel):
    id: str
    display_name: str
    user_id: str | None = None
    managed_by_id: str
    is_child_profile: bool = False
    llm_provider: str = ""
    llm_model: str = ""
    by_task: dict[str, dict[str, str]] = Field(default_factory=dict)
    default_language: str = "de"
    target_age: str = ""
    auto_purge_sources: bool = False
    created_at: str


class ProfileCreateRequest(BaseModel):
    display_name: str = Field(min_length=1, max_length=80)
    is_child_profile: bool = False


class ProfileSettingsUpdateRequest(BaseModel):
    display_name: str | None = Field(default=None, max_length=80)
    llm_provider: str | None = Field(default=None, max_length=32)
    llm_model: str | None = Field(default=None, max_length=80)
    by_task: dict[str, dict[str, str]] | None = None
    default_language: str | None = Field(default=None, max_length=8)
    target_age: str | None = Field(default=None, max_length=32)
    auto_purge_sources: bool | None = None


class ChildCreateRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=12)
    display_name: str = Field(min_length=1, max_length=80)
    parent_id: str | None = None
    parent_ids: list[str] = Field(default_factory=list, max_length=2)


class ChildGuardiansUpdateRequest(BaseModel):
    parent_ids: list[str] = Field(min_length=1, max_length=2)


class UserSettingsUpdateRequest(BaseModel):
    display_name: str | None = Field(default=None, max_length=80)
    llm_provider: str | None = Field(default=None, max_length=32)
    llm_model: str | None = Field(default=None, max_length=80)
    by_task: dict[str, dict[str, str]] | None = None


class AdminCreateUserRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=12)
    display_name: str = Field(default="", max_length=80)
    is_admin: bool = False
    totp_required: bool = False


class AdminUserUpdateRequest(BaseModel):
    display_name: str | None = Field(default=None, max_length=80)


class LoginResponse(BaseModel):
    requires_2fa: bool = False
    must_enroll_2fa: bool = False
    user: UserResponse | None = None


class UserAdminResponse(UserResponse):
    is_active: bool
    created_at: str


class TotpPolicyRequest(BaseModel):
    totp_required: bool


class UnitCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=256)
    brief: str | None = Field(default=None, max_length=8000)
    subject: str | None = Field(default=None, max_length=64)
    language: str = Field(default="de", max_length=8)
    target_age: str | None = Field(default=None, max_length=32)
    difficulty: int = Field(default=1, ge=1, le=5)
    task_type: str = Field(default="mixed", max_length=32)
    math_focus: str | None = Field(default=None, max_length=32)
    auto_purge_sources: bool = False
    profile_id: str | None = None
    profile_ids: list[str] | None = None


class UnitAssignRequest(BaseModel):
    profile_ids: list[str] = Field(min_length=1)


class UnitUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=256)
    brief: str | None = Field(default=None, max_length=8000)
    subject: str | None = Field(default=None, max_length=64)
    language: str | None = Field(default=None, max_length=8)
    target_age: str | None = Field(default=None, max_length=32)
    difficulty: int | None = Field(default=None, ge=1, le=5)
    task_type: str | None = Field(default=None, max_length=32)
    math_focus: str | None = Field(default=None, max_length=32)
    auto_purge_sources: bool | None = None


class UnitGenerateRequest(BaseModel):
    provider: str | None = Field(default=None, max_length=32)


class RecordRebuildRequest(BaseModel):
    difficulty: int | None = Field(default=None, ge=1, le=5)
    task_type: str | None = Field(default=None, max_length=32)


class LearnPositionRequest(BaseModel):
    module_index: int = Field(ge=0)
    phase: Literal["intro", "read", "quiz", "module_done", "complete"]
    question_index: int = Field(default=0, ge=0)


class LearnAnswerRequest(BaseModel):
    module_id: str
    question_index: int = Field(ge=0)
    selected: int = Field(ge=0)


class LearnModuleRequest(BaseModel):
    module_id: str


class SourceUrlRequest(BaseModel):
    url: str = Field(min_length=8, max_length=2048)


class ExamUpdateRequest(BaseModel):
    taken_at: date | None = None
    exam_type: str | None = Field(default=None, max_length=32)
    grade_label: str | None = Field(default=None, max_length=32)
    score: int | None = Field(default=None, ge=0)
    max_score: int | None = Field(default=None, ge=1)
    notes: str | None = Field(default=None, max_length=4000)
    clear_grade: bool = False
    clear_notes: bool = False


class ExamAnalysisUpdateRequest(BaseModel):
    """Manuelle Korrektur der KI-Prüfungsanalyse (strukturiertes JSON)."""

    summary: str | None = Field(default=None, max_length=8000)
    strengths: list[str] | None = None
    gaps: list[str] | None = None
    error_patterns: list[dict] | None = None
    tasks: list[dict] | None = None
    recommendations: list[str] | None = None


class ProjectCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=256)
    description: str | None = Field(default=None, max_length=4096)
    classification: int = Field(default=1, ge=0, le=3)


class ProjectUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=256)
    description: str | None = Field(default=None, max_length=4096)
    version: int = Field(ge=1)


class ProjectResponse(BaseModel):
    id: str
    name: str
    description: str | None
    classification: int
    version: int
    locked_by_id: str | None
    locked_until: str | None
    created_at: str
    updated_at: str


class TaskCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=256)
    body: str | None = Field(default=None, max_length=8192)
    status: str = Field(default="open")
    classification: int = Field(default=1, ge=0, le=3)


class TaskUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=256)
    body: str | None = Field(default=None, max_length=8192)
    status: str | None = None
    version: int = Field(ge=1)


class TaskResponse(BaseModel):
    id: str
    project_id: str
    title: str
    body: str | None
    status: str
    classification: int
    version: int
    locked_by_id: str | None
    locked_until: str | None
    created_at: str
    updated_at: str


class MemberAddRequest(BaseModel):
    user_id: str
    role: Literal["viewer", "member", "manager"] = "member"


class MemberResponse(BaseModel):
    id: str
    user_id: str
    role: str
    created_at: str
