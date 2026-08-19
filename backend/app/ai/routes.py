"""KI-Endpunkte: Status, Test-Complete, TTS."""

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field

from app.ai.catalog import resolve_task_ai
from app.ai.errors import LlmError
from app.ai.providers import complete, provider_status
from app.ai.tts import TtsError, synthesize_openai
from app.core.auth.dependencies import get_app_user
from app.models import User
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
