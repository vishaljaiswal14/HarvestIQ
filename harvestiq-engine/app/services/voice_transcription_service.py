from typing import Optional, Any

from app.core.constants.radar import ALLOWED_AUDIO_TYPES, MAX_AUDIO_BYTES
from app.core.exceptions import bad_gateway, unprocessable_entity
from app.integrations.groq_client import GroqClient
from app.models.day5_schemas import VoiceTranscribeResponse


class VoiceTranscriptionService:
    def __init__(self, gemini_client: Optional[Any] = None) -> None:
        self.gemini_client = gemini_client or GroqClient()

    async def transcribe(
        self,
        audio_bytes: bytes,
        content_type: str,
        language: Optional[str] = None,
    ) -> VoiceTranscribeResponse:
        if not audio_bytes:
            raise unprocessable_entity("Audio file is required")
        if len(audio_bytes) > MAX_AUDIO_BYTES:
            raise unprocessable_entity("Audio file exceeds maximum allowed size")
        if content_type not in ALLOWED_AUDIO_TYPES:
            raise unprocessable_entity("Unsupported audio type")

        try:
            result = await self.gemini_client.transcribe_audio(
                audio_bytes=audio_bytes,
                mime_type=content_type,
                language=language,
            )
        except Exception as exc:
            raise bad_gateway(f"Gemini transcription unavailable: {exc}") from exc

        transcript = str(result["transcript"]).strip()
        if not transcript:
            raise unprocessable_entity("Could not transcribe audio")

        return VoiceTranscribeResponse(
            transcript=transcript,
            confidence=float(result["confidence"]),
            language=language or "auto",
        )
