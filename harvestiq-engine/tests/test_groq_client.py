from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.integrations.groq_client import GroqClient


@pytest.mark.asyncio
async def test_groq_client_transcribe_audio() -> None:
    client = GroqClient(api_key="test-groq-key")
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {
        "text": "Transcribed wheat crop issue spoken in Hindi."
    }

    with patch("app.integrations.groq_client.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client_cls.return_value = mock_client

        result = await client.transcribe_audio(b"fakeaudiobytes", "audio/webm", "hi")

    assert result["transcript"] == "Transcribed wheat crop issue spoken in Hindi."
    assert result["confidence"] == 1.0

    url = mock_client.post.call_args.args[0]
    headers = mock_client.post.call_args.kwargs["headers"]
    files = mock_client.post.call_args.kwargs["files"]
    data = mock_client.post.call_args.kwargs["data"]

    assert url == "https://api.groq.com/openai/v1/audio/transcriptions"
    assert headers["Authorization"] == "Bearer test-groq-key"
    assert "file" in files
    assert files["file"][0] == "audio.webm"
    assert files["file"][1] == b"fakeaudiobytes"
    assert data["model"] == "whisper-large-v3"
    assert data["language"] == "hi"
    assert "NPK" in data["prompt"]
