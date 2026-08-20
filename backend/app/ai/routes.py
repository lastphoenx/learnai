"""KI-Endpunkte: Status, Test-Complete, TTS, Diagnose."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.ai.catalog import resolve_task_ai
from app.ai.effective import effective_ai_config
from app.ai.errors import LlmError
from app.ai.providers import complete, provider_status
from app.ai.tts import TtsError, synthesize_openai
from app.core.auth.dependencies import get_app_user
from app.core.db import get_db
from app.models import LearningProfile, User
from app.services.profile_service import ProfileError, get_profile_for_actor, resolve_prefs_for_profile
from app.services.unit_service import UnitError, get_unit
from app.services.user_service import get_user_settings

router = APIRouter(prefix="/ai", tags=["ai"])


class TtsRequest(BaseModel):
    text: str = Field(min_length=1, max_length=4096)
    lang: str = Field(default="de", max_length=8)


class CompleteRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=4000)
    provider: str | None = Field(default=None, max_length=32)


@router.get("/status")
def status(user: User = Depends(get_app_user)):
    del user
    return provider_status()


@router.get("/effective")
def ai_effective(
    user: User = Depends(get_app_user),
    db: Session = Depends(get_db),
    unit_id: UUID | None = Query(default=None),
    profile_id: UUID | None = Query(default=None),
):
    """Aufgelöste KI-Modelle: .env-Fallback + Lerner-Profil (optional für Einheit/Profil)."""
    prefs: dict = {}
    context: dict = {"unit_id": str(unit_id) if unit_id else None, "profile_id": str(profile_id) if profile_id else None}

    if unit_id:
        try:
            unit_data = get_unit(db, user, unit_id)
            context["unit_title"] = unit_data.get("title")
            pid = unit_data.get("profile_id")
            if pid:
                context["profile_id"] = pid
                prefs = resolve_prefs_for_profile(db, UUID(pid))
        except UnitError as exc:
            raise HTTPException(status_code=404, detail=exc.message) from exc
    elif profile_id:
        try:
            profile = get_profile_for_actor(db, user, profile_id)
            context["profile_name"] = profile.display_name
            prefs = resolve_prefs_for_profile(db, profile_id)
        except ProfileError as exc:
            code = 404 if exc.code == "not_found" else 403
            raise HTTPException(status_code=code, detail=exc.message) from exc
    else:
        prefs = get_user_settings(user)
        profile = db.get(LearningProfile, user.profile_id) if user.profile_id else None
        if profile:
            prefs = resolve_prefs_for_profile(db, profile.id)
            context["profile_id"] = str(profile.id)
            context["profile_name"] = profile.display_name

    out = effective_ai_config(prefs)
    out["context"] = context
    return out


@router.post("/complete")
def complete_prompt(body: CompleteRequest, user: User = Depends(get_app_user)):
    del user
    try:
        return complete(prompt=body.prompt, provider=body.provider)
    except LlmError as exc:
        raise HTTPException(status_code=400, detail=exc.message) from exc


@router.post("/tts")
def tts(body: TtsRequest, user: User = Depends(get_app_user)):
    prefs = get_user_settings(user)
    provider, model = resolve_task_ai(prefs, "tts")
    if provider != "openai":
        raise HTTPException(
            status_code=400,
            detail="Vorlesen ist nur mit OpenAI-TTS eingebaut. In den Einstellungen TTS auf OpenAI stellen.",
        )
    try:
        audio = synthesize_openai(body.text, body.lang, model=model)
        return Response(content=audio, media_type="audio/mpeg")
    except TtsError as exc:
        raise HTTPException(status_code=400, detail=exc.message) from exc
