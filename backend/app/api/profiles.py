"""Lerner-Profile API."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.auth.dependencies import get_current_user, require_admin
from app.core.db import get_db
from app.models import User
from app.schemas import ProfileCreateRequest, ProfileResponse, ProfileSettingsUpdateRequest
from app.services.profile_service import (
    ProfileError,
    apply_recommended_settings,
    create_profile,
    get_profile_for_actor,
    list_manageable_profiles,
    profile_public_dict,
    set_profile_settings,
)

router = APIRouter(prefix="/profiles", tags=["profiles"])


@router.get("", response_model=list[ProfileResponse])
def profiles_list(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return [ProfileResponse(**row) for row in list_manageable_profiles(db, user)]


@router.post("", response_model=ProfileResponse, status_code=status.HTTP_201_CREATED)
def profiles_create(
    body: ProfileCreateRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if user.is_child:
        raise HTTPException(status_code=403, detail="Kinder-Accounts dürfen keine Profile anlegen")
    try:
        profile = create_profile(
            db,
            user,
            display_name=body.display_name,
            is_child_profile=body.is_child_profile,
        )
        db.commit()
        db.refresh(profile)
        return ProfileResponse(**profile_public_dict(profile))
    except ProfileError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=exc.message) from exc


@router.get("/{profile_id}", response_model=ProfileResponse)
def profiles_get(
    profile_id: UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        profile = get_profile_for_actor(db, user, profile_id)
        return ProfileResponse(**profile_public_dict(profile))
    except ProfileError as exc:
        raise HTTPException(status_code=404 if exc.code == "not_found" else 403, detail=exc.message) from exc


@router.patch("/{profile_id}", response_model=ProfileResponse)
def profiles_update(
    profile_id: UUID,
    body: ProfileSettingsUpdateRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        profile = get_profile_for_actor(db, user, profile_id)
        payload = body.model_dump(exclude_unset=True)
        set_profile_settings(db, profile, payload)
        db.commit()
        db.refresh(profile)
        return ProfileResponse(**profile_public_dict(profile))
    except ProfileError as exc:
        db.rollback()
        code = 400
        if exc.code == "not_found":
            code = 404
        elif exc.code == "forbidden":
            code = 403
        raise HTTPException(status_code=code, detail=exc.message) from exc


@router.post("/{profile_id}/apply-recommendations", response_model=ProfileResponse)
def profiles_apply_recommendations(
    profile_id: UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        profile = get_profile_for_actor(db, user, profile_id)
        apply_recommended_settings(db, profile)
        db.commit()
        db.refresh(profile)
        return ProfileResponse(**profile_public_dict(profile))
    except ProfileError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=exc.message) from exc
