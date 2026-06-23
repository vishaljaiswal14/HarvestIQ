from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from app.integrations.gemini_client import OpenRouterClient
from app.services.voice_transcription_service import VoiceTranscriptionService


@pytest.mark.asyncio
async def test_transcribe_returns_text() -> None:
    gemini = MagicMock(spec=OpenRouterClient)
    gemini.transcribe_audio = AsyncMock(return_value={"transcript": "मेरी गेहूं की फसल में क्या समस्या है?", "confidence": 0.93})

    service = VoiceTranscriptionService(gemini_client=gemini)
    result = await service.transcribe(b"audio", "audio/webm", "hi")

    assert "गेहूं" in result.transcript
    assert result.confidence == 0.93


@pytest.mark.asyncio
async def test_empty_audio_returns_422() -> None:
    service = VoiceTranscriptionService(MagicMock())
    with pytest.raises(HTTPException) as exc:
        await service.transcribe(b"", "audio/webm")
    assert exc.value.status_code == 422


@pytest.mark.asyncio
async def test_gemini_failure_returns_502() -> None:
    gemini = MagicMock(spec=OpenRouterClient)
    gemini.transcribe_audio = AsyncMock(side_effect=RuntimeError("down"))

    service = VoiceTranscriptionService(gemini_client=gemini)
    with pytest.raises(HTTPException) as exc:
        await service.transcribe(b"abc", "audio/webm")
    assert exc.value.status_code == 502
