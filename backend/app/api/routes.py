from uuid import UUID

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app import config
from app.core.auth.dependencies import get_challenge_token, get_current_user, require_admin
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
    LoginRequest,
    LoginResponse,
    RegisterRequest,
    TotpPolicyRequest,
    TwoFactorConfirmRequest,
    TwoFactorSetupResponse,
    TwoFactorVerifyRequest,
    UserAdminResponse,
    UserResponse,
)
from app.services.user_service import (
    AuthError,
    authenticate_password,
    complete_2fa_login,
    confirm_totp,
    list_users_admin,
    register_user,
    set_totp_required,
    setup_totp,
    start_2fa_challenge,
    user_public_dict,
)

auth_router = APIRouter(prefix="/auth", tags=["auth"])
users_router = APIRouter(prefix="/users", tags=["users"])


def _user_response(user: User) -> UserResponse:
    return UserResponse(**user_public_dict(user))


def _finish_login(db: Session, user: User, response: Response) -> LoginResponse:
    token, _ = create_session(db, user.id)
    db.commit()
    set_session_cookie(response, token)
    clear_challenge_cookie(response)
    public = user_public_dict(user)
    return LoginResponse(user=_user_response(user), must_enroll_2fa=public["must_enroll_2fa"])


@auth_router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(body: RegisterRequest, db: Session = Depends(get_db)):
    if not config.settings.allow_registration:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Registrierung deaktiviert")
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
def login(body: LoginRequest, response: Response, db: Session = Depends(get_db)):
    try:
        user = authenticate_password(db, body.email, body.password)
        if user.totp_enabled:
            challenge = start_2fa_challenge(db, user)
            db.commit()
            set_challenge_cookie(response, challenge)
            return LoginResponse(requires_2fa=True)
        return _finish_login(db, user, response)
    except AuthError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=exc.message) from exc


@auth_router.post("/2fa/verify", response_model=LoginResponse)
def verify_2fa(
    body: TwoFactorVerifyRequest,
    response: Response,
    db: Session = Depends(get_db),
    challenge_token: str = Depends(get_challenge_token),
):
    if not body.totp_code and not body.recovery_code:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Code erforderlich")
    try:
        user = complete_2fa_login(
            db,
            challenge_token,
            totp_code=body.totp_code,
            recovery_code=body.recovery_code,
        )
        return _finish_login(db, user, response)
    except AuthError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=exc.message) from exc


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


@auth_router.post("/2fa/setup", response_model=TwoFactorSetupResponse)
def totp_setup(
    body: LoginRequest,
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
