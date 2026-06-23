from unittest.mock import AsyncMock, MagicMock

from bson import ObjectId
from fastapi.testclient import TestClient

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.core.database import get_database
from app.core.twilio_security import compute_twilio_signature
from app.main import create_app


def _build_client(monkeypatch, **env: str) -> TestClient:
    base_env = {
        "MONGODB_URI": "mongodb://localhost:27017",
        "JWT_SECRET_KEY": "test-secret-key",
        "ENVIRONMENT": "development",
    }
    base_env.update(env)
    for key, value in base_env.items():
        monkeypatch.setenv(key, value)

    get_settings.cache_clear()
    monkeypatch.setattr("app.main.connect_to_mongo", AsyncMock())
    monkeypatch.setattr("app.main.ensure_indexes", AsyncMock())
    monkeypatch.setattr("app.main.close_mongo_connection", AsyncMock())

    app = create_app()
    mock_db = MagicMock()
    app.dependency_overrides[get_database] = lambda: mock_db
    app.state.db = mock_db
    return TestClient(app)


def test_verification_log_requires_authentication(monkeypatch) -> None:
    client = _build_client(monkeypatch)

    response = client.post(
        "/api/v1/verification/log",
        json={
            "event_type": "smoke-test",
            "environment": "development",
            "status": "ok",
            "details": {},
        },
    )

    assert response.status_code == 401


def test_demo_seed_disabled_in_production(monkeypatch) -> None:
    client = _build_client(monkeypatch, ENVIRONMENT="production")

    async def fake_user():
        return {"_id": ObjectId(), "preferred_lang": "en", "role": "FARMER"}

    client.app.dependency_overrides[get_current_user] = fake_user

    response = client.post("/api/v1/demo/seed")

    assert response.status_code == 403
    assert response.json()["detail"] == "Demo seeding is disabled in this environment"


def test_sos_callback_rejects_invalid_signature_in_production(monkeypatch) -> None:
    client = _build_client(
        monkeypatch,
        ENVIRONMENT="production",
        TWILIO_ACCOUNT_SID="AC123456789",
        TWILIO_AUTH_TOKEN="twilio-auth-token",
        TWILIO_FROM_NUMBER="+15555550123",
        EXTERNAL_CALLBACK_URL="https://example.com",
    )

    response = client.post(
        "/api/v1/sos/status-callback",
        data={"MessageSid": "SM123", "MessageStatus": "delivered"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Invalid Twilio signature"


def test_sos_callback_accepts_valid_signature_in_production(monkeypatch) -> None:
    client = _build_client(
        monkeypatch,
        ENVIRONMENT="production",
        TWILIO_ACCOUNT_SID="AC123456789",
        TWILIO_AUTH_TOKEN="twilio-auth-token",
        TWILIO_FROM_NUMBER="+15555550123",
        EXTERNAL_CALLBACK_URL="https://example.com",
    )

    client.app.state.db.sos_actions.find_one = AsyncMock(return_value=None)
    payload = {"MessageSid": "SM123", "MessageStatus": "delivered"}
    signature = compute_twilio_signature(
        "https://example.com/api/v1/sos/status-callback",
        payload,
        "twilio-auth-token",
    )

    response = client.post(
        "/api/v1/sos/status-callback",
        data=payload,
        headers={"X-Twilio-Signature": signature},
    )

    assert response.status_code == 200
    assert response.json() == {"status": "success"}
