"""KI-Hilfsendpunkte (TTS zuerst; Kursgenerierung folgt)."""

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field

from app.core.auth.dependencies import get_app_user
from app.models import User
from app.ai.tts import TtsError, synthesize_openai

router = APIRouter(prefix="/ai", tags=["ai"])


class TtsRequest(BaseModel):
    text: str = Field(min_length=1, max_length=4096)
    lang: str = Field(default="de", max_length=8)


@router.post("/tts")
def tts(body: TtsRequest, user: User = Depends(get_app_user)):
    del user
    try:
        audio = synthesize_openai(body.text, body.lang)
        return Response(content=audio, media_type="audio/mpeg")
    except TtsError as exc:
        raise HTTPException(status_code=400, detail=exc.message) from exc
