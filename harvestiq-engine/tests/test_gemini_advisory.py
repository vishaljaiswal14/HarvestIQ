from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.integrations.gemini_client import OpenRouterClient


@pytest.mark.asyncio
async def test_synthesize_advisory_calls_generate_content() -> None:
    client = OpenRouterClient(api_key="test-key", text_model="gemini-2.0-flash")
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {
        "candidates": [{"content": {"parts": [{"text": "Your wheat crop shows heat stress."}]}}]
    }

    with patch("app.integrations.gemini_client.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client_cls.return_value = mock_client

        result = await client.synthesize_advisory("# context", "en", mitigation_locked=True)

    assert "heat stress" in result.lower()
    payload = mock_client.post.call_args.kwargs["json"]
    assert "mitigation is locked" in payload["systemInstruction"]["parts"][0]["text"].lower()


@pytest.mark.asyncio
async def test_detect_disease_calls_openrouter() -> None:
    client = OpenRouterClient(api_key="test-openrouter-key", model="google/gemini-2.0-flash")
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": '{"crop_type": "WHEAT", "disease_tag": "WHEAT_RUST", "confidence": 0.95}'
                }
            }
        ]
    }

    with patch("app.integrations.gemini_client.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client_cls.return_value = mock_client

        result = await client.detect_disease(b"fakeimagebytes", "image/png", "WHEAT", "Rajasthan")

    assert result["disease"] == "WHEAT_RUST"
    assert result["confidence"] == 0.95
    
    headers = mock_client.post.call_args.kwargs["headers"]
    payload = mock_client.post.call_args.kwargs["json"]
    assert headers["Authorization"] == "Bearer test-openrouter-key"
    assert payload["model"] == "google/gemini-2.0-flash"
    assert "data:image/png;base64," in payload["messages"][0]["content"][1]["image_url"]["url"]


@pytest.mark.asyncio
async def test_transcribe_audio_calls_gemini() -> None:
    client = OpenRouterClient(api_key="test-api-key", text_model="gemini-2.0-flash")
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {"text": "Transcribed text sample"}
                    ]
                }
            }
        ]
    }

    with patch("app.integrations.gemini_client.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client_cls.return_value = mock_client

        result = await client.transcribe_audio(b"fakeaudiobytes", "audio/webm", "en")

    assert result["transcript"] == "Transcribed text sample"
    assert result["confidence"] == 1.0

    url = mock_client.post.call_args.args[0]
    headers = mock_client.post.call_args.kwargs["headers"]
    payload = mock_client.post.call_args.kwargs["json"]

    assert "test-api-key" in url
    assert headers["x-goog-api-key"] == "test-api-key"
    assert "inlineData" in payload["contents"][0]["parts"][1]


@pytest.mark.asyncio
async def test_detect_disease_calls_groq_vision_directly() -> None:
    mock_settings = MagicMock()
    mock_settings.openrouter_api_key = ""
    mock_settings.groq_api_key = "test-groq-key"

    with patch("app.integrations.gemini_client.get_settings", return_value=mock_settings):
        client = OpenRouterClient()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": '{"crop_type": "WHEAT", "disease_tag": "WHEAT_RUST", "confidence": 0.95}'
                    }
                }
            ]
        }

        with patch("app.integrations.gemini_client.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_cls.return_value = mock_client

            result = await client.detect_disease(b"fakeimagebytes", "image/png", "WHEAT", "Rajasthan")

        assert result["disease"] == "WHEAT_RUST"
        assert result["confidence"] == 0.95

        url = mock_client.post.call_args.args[0]
        headers = mock_client.post.call_args.kwargs["headers"]
        payload = mock_client.post.call_args.kwargs["json"]

        assert "api.groq.com" in url
        assert headers["Authorization"] == "Bearer test-groq-key"
        assert payload["model"] == "meta-llama/llama-4-scout-17b-16e-instruct"
        assert payload["messages"][0]["content"][0]["text"].startswith("You are an agricultural")
        assert "data:image/png;base64," in payload["messages"][0]["content"][1]["image_url"]["url"]




