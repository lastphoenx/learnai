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
    totp_enabled: bool
    totp_required: bool
    must_enroll_2fa: bool = False


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
    auto_purge_sources: bool = False


class UnitUpdateRequest(BaseModel):
    auto_purge_sources: bool | None = None


class UnitGenerateRequest(BaseModel):
    provider: str | None = Field(default=None, max_length=32)


class RecordRebuildRequest(BaseModel):
    difficulty: int | None = Field(default=None, ge=1, le=5)


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
