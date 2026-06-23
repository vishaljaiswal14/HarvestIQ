import httpx
from typing import Optional
from app.core.config import get_settings


class GroqClient:
    def __init__(self, api_key: Optional[str] = None):
        settings = get_settings()
        self.api_key = (
            api_key
            or getattr(settings, "groq_api_key", "")
            or getattr(settings, "openrouter_api_key", "")  # Fallback helper if key reuse matches
        )
        self.model = "whisper-large-v3"
        self.url = "https://api.groq.com/openai/v1/audio/transcriptions"

    async def transcribe_audio(
        self,
        audio_bytes: bytes,
        mime_type: str,
        language: Optional[str] = None,
    ) -> dict:
        if not self.api_key:
            raise RuntimeError("GROQ_API_KEY is not configured")

        ext = "webm" if "webm" in mime_type else "wav"
        files = {
            "file": (f"audio.{ext}", audio_bytes, mime_type)
        }

        data = {
            "model": self.model,
            "response_format": "json"
        }

        if language and language != "auto":
            data["language"] = language

        # Seed prompting to direct spelling correctness of crop indicators and acronyms
        data["prompt"] = "agricultural, farm, crop, NPK, FSI, wheat, paddy, soil, fertilizer, yield"

        headers = {
            "Authorization": f"Bearer {self.api_key}"
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.url,
                headers=headers,
                files=files,
                data=data,
                timeout=30.0,
            )

        response.raise_for_status()
        res_data = response.json()

        transcript = res_data.get("text", "").strip()

        return {
            "transcript": transcript,
            "confidence": 1.0
        }
