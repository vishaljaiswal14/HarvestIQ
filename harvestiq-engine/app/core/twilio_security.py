import base64
import hashlib
import hmac
from typing import Any, Iterable
from urllib.parse import urlencode


LOCAL_CALLBACK_HOST_MARKERS = ("localhost", "127.0.0.1", "0.0.0.0", ".local")


def is_local_callback_url(url: str | None) -> bool:
    if not url:
        return False
    return any(marker in url for marker in LOCAL_CALLBACK_HOST_MARKERS)


def build_signature_payload(url: str, params: dict[str, Any]) -> str:
    payload = url
    for key in sorted(params):
        value = params[key]
        if isinstance(value, (list, tuple)):
            items: Iterable[Any] = value
        else:
            items = (value,)
        for item in items:
            payload += f"{key}{item}"
    return payload


def compute_twilio_signature(url: str, params: dict[str, Any], auth_token: str) -> str:
    payload = build_signature_payload(url, params).encode("utf-8")
    digest = hmac.new(auth_token.encode("utf-8"), payload, hashlib.sha1).digest()
    return base64.b64encode(digest).decode("utf-8")


def is_valid_twilio_signature(
    url: str,
    params: dict[str, Any],
    signature: str | None,
    auth_token: str,
) -> bool:
    if not signature or not auth_token:
        return False
    expected = compute_twilio_signature(url, params, auth_token)
    return hmac.compare_digest(expected, signature)


def build_external_request_url(base_url: str, path: str, query_params: dict[str, Any] | None = None) -> str:
    url = f"{base_url.rstrip('/')}{path}"
    if query_params:
        query_string = urlencode(query_params, doseq=True)
        if query_string:
            url = f"{url}?{query_string}"
    return url
