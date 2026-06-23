import json
import logging
from typing import Any
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.database import get_database

logger = logging.getLogger(__name__)

# In-memory translation dictionary cache: lang -> {english_phrase/key: translation}
_LOCALIZATION_CACHE = {}


async def _get_localization_dict(lang: str) -> dict[str, str]:
    if lang in _LOCALIZATION_CACHE:
        return _LOCALIZATION_CACHE[lang]

    try:
        from app.core.database import get_database
        db = get_database()
    except Exception as exc:
        logger.warning(f"Database not initialized for localization middleware: {exc}")
        return {}

    try:
        cursor = db.localization_dictionary.find({"lang": lang})
        dictionary = {}

        # Also load English values to map English source phrases directly to translations
        en_cursor = db.localization_dictionary.find({"lang": "en"})
        en_map = {}
        async for doc in en_cursor:
            en_map[doc["key"]] = doc["value"]
            dictionary[doc["value"]] = doc["value"]

        async for doc in cursor:
            key = doc["key"]
            val = doc["value"]
            dictionary[key] = val
            if key in en_map:
                en_val = en_map[key]
                dictionary[en_val] = val

        _LOCALIZATION_CACHE[lang] = dictionary
        return dictionary
    except Exception as e:
        logger.error(f"Failed to load localization dictionary for {lang}: {e}")
        return {}


def _translate_value(val: Any, dictionary: dict[str, str]) -> Any:
    if isinstance(val, str):
        if val in dictionary:
            return dictionary[val]
        # Case-insensitive lookup fallback
        val_lower = val.strip().lower()
        for k, v in dictionary.items():
            if k.strip().lower() == val_lower:
                return v
        return val
    elif isinstance(val, dict):
        return {k: _translate_value(v, dictionary) for k, v in val.items()}
    elif isinstance(val, list):
        return [_translate_value(item, dictionary) for item in val]
    return val


class LocalizationMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        accept_lang = request.headers.get("accept-language", "hi")
        # Extract primary locale (e.g. "hi-IN" -> "hi")
        lang = accept_lang.split(",")[0].split(";")[0].strip().lower()
        if lang not in ["hi", "en", "mr"]:
            lang = "hi"

        response = await call_next(request)

        # Only process JSON responses
        content_type = response.headers.get("content-type", "")
        if "application/json" not in content_type:
            return response

        # Fast path for empty/no-content responses
        if response.status_code in [204, 304]:
            return response

        dictionary = await _get_localization_dict(lang)
        if not dictionary:
            return response

        # Read the body safely depending on response type
        if hasattr(response, "body"):
            body = response.body
        else:
            body = b""
            async for chunk in response.body_iterator:
                body += chunk

        try:
            # Attempt to read and parse the response body as JSON
            response_body = body.decode("utf-8")
            data = json.loads(response_body)
            translated_data = _translate_value(data, dictionary)
            new_body = json.dumps(translated_data, ensure_ascii=False).encode("utf-8")

            response.headers["content-length"] = str(len(new_body))
            return Response(
                content=new_body,
                status_code=response.status_code,
                headers=dict(response.headers),
                media_type=response.media_type,
            )
        except (json.JSONDecodeError, ValueError, AttributeError) as e:
            # If it's empty, HTML, or raw text, bypass translation and return cleanly
            print("[LocalizationMiddleware] Non-JSON payload detected. Bypassing translation safely.")
            if not hasattr(response, "body") and body:
                return Response(
                    content=body,
                    status_code=response.status_code,
                    headers=dict(response.headers),
                    media_type=response.media_type,
                )
            return response

