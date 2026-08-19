from uuid import UUID

import logging

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app import config
from app.core.auth.dependencies import get_app_user, get_challenge_token, get_current_user, require_admin
from app.core.auth import bruteforce
from app.core.auth.client_ip import get_client_ip, log_client_ip
from app.core.auth.sessions import (
    clear_challenge_cookie,
    clear_session_cookie,
    create_session,
    revoke_session,
    set_challenge_cookie,
    set_session_cookie,
)
from app.core.db import get_db
from app.models import User
from app.schemas import (
    AdminCreateUserRequest,
    AdminUserUpdateRequest,
    ChildCreateRequest,
    ChildGuardiansUpdateRequest,
    LoginRequest,
    LoginResponse,
    RegisterRequest,
    TotpPolicyRequest,
    TwoFactorConfirmRequest,
    TwoFactorSetupRequest,
    TwoFactorSetupResponse,
    TwoFactorVerifyRequest,
    UserAdminResponse,
    UserResponse,
    UserSettingsUpdateRequest,
)
from app.services.user_service import (
    AuthError,
    admin_create_user,
    authenticate_password,
    complete_2fa_login,
    confirm_totp,
    create_child_user,
    find_user_by_email,
    list_users_admin,
    register_user,
    set_totp_required,
    setup_totp,
    start_2fa_challenge,
    update_child_guardians,
    update_user_settings,
    user_public_dict,
)

auth_router = APIRouter(prefix="/auth", tags=["auth"])
users_router = APIRouter(prefix="/users", tags=["users"])


def _user_response(user: User) -> UserResponse:
    return UserResponse(**user_public_dict(user))


def _finish_login(db: Session, user: User, response: Response) -> LoginResponse:
    token, _ = create_session(db, user.id)
    db.commit()
    db.refresh(user)
    set_session_cookie(response, token)
    clear_challenge_cookie(response)
    public = user_public_dict(user)
    return LoginResponse(user=_user_response(user), must_enroll_2fa=public["must_enroll_2fa"])


@auth_router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(body: RegisterRequest, request: Request, db: Session = Depends(get_db)):
    if not config.settings.allow_registration:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Registrierung deaktiviert")
    ip = get_client_ip(request)
    bruteforce.assert_login_allowed(ip=ip, email=body.email)
    try:
        user = register_user(
            db,
            email=body.email,
            password=body.password,
            display_name=body.display_name,
        )
        db.commit()
        return _user_response(user)
    except AuthError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.message) from exc


@auth_router.post("/login", response_model=LoginResponse)
def login(body: LoginRequest, request: Request, response: Response, db: Session = Depends(get_db)):
    log_client_ip(request, context="login_attempt", email=body.email)
    ip = get_client_ip(request)
    try:
        bruteforce.assert_login_allowed(ip=ip, email=body.email)
        if config.settings.login_allowlist_only:
            known = find_user_by_email(db, body.email)
            if not known:
                bruteforce.record_unknown_email(ip=ip, email=body.email)
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Ungültige Anmeldedaten",
                )
        user = authenticate_password(db, body.email, body.password)
        bruteforce.record_success(ip=ip, email=body.email)
        log_client_ip(request, context="login_ok", email=body.email)
        if user.totp_enabled:
            challenge = start_2fa_challenge(db, user)
            db.commit()
            set_challenge_cookie(response, challenge)
            return LoginResponse(requires_2fa=True)
        return _finish_login(db, user, response)
    except AuthError as exc:
        db.rollback()
        bruteforce.record_failed_login(ip=ip, email=body.email)
        log_client_ip(request, context="login_failed", email=body.email)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=exc.message) from exc
    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        logging.getLogger(__name__).exception("login failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Interner Fehler bei der Anmeldung",
        ) from exc


@auth_router.post("/2fa/verify", response_model=LoginResponse)
def verify_2fa(
    body: TwoFactorVerifyRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    challenge_token: str = Depends(get_challenge_token),
):
    ip = get_client_ip(request)
    if not body.totp_code and not body.recovery_code:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Code erforderlich")
    try:
        bruteforce.assert_2fa_allowed(ip=ip)
        user = complete_2fa_login(
            db,
            challenge_token,
            totp_code=body.totp_code,
            recovery_code=body.recovery_code,
        )
        bruteforce.record_success(ip=ip)
        return _finish_login(db, user, response)
    except AuthError as exc:
        db.rollback()
        bruteforce.record_failed_2fa(ip=ip)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=exc.message) from exc
    except HTTPException:
        db.rollback()
        raise


@auth_router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    response: Response,
    db: Session = Depends(get_db),
    session_token: str | None = Cookie(default=None, alias=config.settings.cookie_name),
):
    if session_token:
        revoke_session(db, session_token)
    clear_session_cookie(response)
    clear_challenge_cookie(response)
    db.commit()


@auth_router.get("/me", response_model=UserResponse)
def me(user: User = Depends(get_current_user)):
    return _user_response(user)


@auth_router.patch("/me", response_model=UserResponse)
def me_update(
    body: UserSettingsUpdateRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        if body.display_name is not None:
            update_user_settings(db, user, display_name=body.display_name)
        if any(v is not None for v in (body.llm_provider, body.llm_model, body.by_task)):
            update_user_settings(
                db,
                user,
                llm_provider=body.llm_provider,
                llm_model=body.llm_model,
                by_task=body.by_task,
            )
        db.commit()
        db.refresh(user)
        return _user_response(user)
    except AuthError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.message) from exc


@auth_router.post("/2fa/setup", response_model=TwoFactorSetupResponse)
def totp_setup(
    body: TwoFactorSetupRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        secret, uri = setup_totp(db, user, body.email)
        db.commit()
        return TwoFactorSetupResponse(provisioning_uri=uri, secret=secret)
    except AuthError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.message) from exc


@auth_router.post("/2fa/confirm")
def totp_confirm(
    body: TwoFactorConfirmRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        codes = confirm_totp(db, user, body.code, body.email)
        db.commit()
        return {"recovery_codes": codes}
    except AuthError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.message) from exc


@users_router.get("", response_model=list[UserAdminResponse])
def users_list(admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    return [UserAdminResponse(**row) for row in list_users_admin(db, admin)]


@users_router.post("", response_model=UserAdminResponse, status_code=status.HTTP_201_CREATED)
def users_create(
    body: AdminCreateUserRequest,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    try:
        user = admin_create_user(
            db,
            admin,
            email=body.email,
            password=body.password,
            display_name=body.display_name,
            is_admin=body.is_admin,
            totp_required=body.totp_required,
        )
        db.commit()
        db.refresh(user)
        row = {**user_public_dict(user), "is_active": user.is_active, "created_at": user.created_at.isoformat()}
        return UserAdminResponse(**row)
    except AuthError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.message) from exc


@users_router.post("/children", response_model=UserAdminResponse, status_code=status.HTTP_201_CREATED)
def users_create_child(
    body: ChildCreateRequest,
    actor: User = Depends(get_app_user),
    db: Session = Depends(get_db),
):
    if actor.is_child:
        raise HTTPException(status_code=403, detail="Kinder-Accounts dürfen keine Kinder anlegen")
    try:
        parent_uuids: list[UUID] = []
        if body.parent_ids:
            parent_uuids = [UUID(pid) for pid in body.parent_ids]
        elif body.parent_id:
            parent_uuids = [UUID(body.parent_id)]
        child = create_child_user(
            db,
            actor,
            email=body.email,
            password=body.password,
            display_name=body.display_name,
            parent_ids=parent_uuids or None,
        )
        db.commit()
        db.refresh(child)
        row = {
            **user_public_dict(child),
            "is_active": child.is_active,
            "created_at": child.created_at.isoformat(),
        }
        return UserAdminResponse(**row)
    except AuthError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.message) from exc


@users_router.patch("/{user_id}/guardians", response_model=UserAdminResponse)
def users_update_guardians(
    user_id: UUID,
    body: ChildGuardiansUpdateRequest,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    target = db.get(User, user_id)
    if not target or target.tenant_id != admin.tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Benutzer nicht gefunden")
    try:
        parent_uuids = [UUID(pid) for pid in body.parent_ids]
        update_child_guardians(db, admin, target, parent_uuids)
        db.commit()
        db.refresh(target)
        row = {
            **user_public_dict(target),
            "is_active": target.is_active,
            "created_at": target.created_at.isoformat(),
        }
        return UserAdminResponse(**row)
    except AuthError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.message) from exc


@users_router.patch("/{user_id}", response_model=UserAdminResponse)
def users_update(
    user_id: UUID,
    body: AdminUserUpdateRequest,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    target = db.get(User, user_id)
    if not target or target.tenant_id != admin.tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Benutzer nicht gefunden")
    try:
        update_user_settings(db, target, display_name=body.display_name)
        db.commit()
        db.refresh(target)
        row = {
            **user_public_dict(target),
            "is_active": target.is_active,
            "created_at": target.created_at.isoformat(),
        }
        return UserAdminResponse(**row)
    except AuthError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.message) from exc


@users_router.patch("/{user_id}/totp-policy", response_model=UserResponse)
def users_totp_policy(
    user_id: UUID,
    body: TotpPolicyRequest,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    target = db.get(User, user_id)
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Benutzer nicht gefunden")
    try:
        updated = set_totp_required(db, admin, target, body.totp_required)
        db.commit()
        db.refresh(updated)
        return _user_response(updated)
    except AuthError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.message) from exc
