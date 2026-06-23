from typing import Annotated, Optional

from fastapi import APIRouter, Depends, File, Form, UploadFile

from app.api.deps import get_current_user
from app.models.day5_schemas import VoiceTranscribeResponse
from app.services.voice_transcription_service import VoiceTranscriptionService

router = APIRouter(prefix="/voice", tags=["voice"])


@router.post("/transcribe", response_model=VoiceTranscribeResponse)
async def transcribe_voice(
    audio: Annotated[UploadFile, File(...)],
    current_user: Annotated[dict, Depends(get_current_user)],
    language: Annotated[Optional[str], Form()] = None,
) -> VoiceTranscribeResponse:
    _ = current_user
    content_type = audio.content_type or "application/octet-stream"
    audio_bytes = await audio.read()
    service = VoiceTranscriptionService()
    resolved_language = language or None
    return await service.transcribe(audio_bytes, content_type, resolved_language)
