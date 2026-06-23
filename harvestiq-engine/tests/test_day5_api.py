from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from bson import ObjectId
from fastapi.testclient import TestClient

from app.api.deps import get_current_user
from app.core.database import get_database
from app.main import create_app
from app.models.day5_schemas import (
    AdvisoryAskResponse,
    DiseaseRadarNearbyResponse,
    LocalizationResponse,
    VoiceTranscribeResponse,
)

USER_ID = str(ObjectId())
FARM_ID = str(ObjectId())


@pytest.fixture
def client(monkeypatch) -> TestClient:
    monkeypatch.setattr("app.main.connect_to_mongo", AsyncMock())
    monkeypatch.setattr("app.main.ensure_indexes", AsyncMock())
    monkeypatch.setattr("app.main.close_mongo_connection", AsyncMock())

    app = create_app()

    async def fake_user():
        return {
            "_id": ObjectId(USER_ID),
            "preferred_lang": "hi",
            "role": "FARMER",
        }

    app.dependency_overrides[get_current_user] = fake_user
    app.dependency_overrides[get_database] = lambda: MagicMock()

    monkeypatch.setattr(
        "app.api.v1.advisory.AdvisoryService.ask",
        AsyncMock(
            return_value=AdvisoryAskResponse(
                advisory_id=str(ObjectId()),
                farm_id=FARM_ID,
                synthesis="Test synthesis",
                language="hi",
                explainability={
                    "summary": "Grounded",
                    "inputs": {"fsi": 0.5},
                    "primary_factor": "THERMAL",
                },
                citations=[],
                intelligence_snapshot_version="v3",
            )
        ),
    )
    monkeypatch.setattr(
        "app.api.v1.disease_radar.DiseaseRadarService.nearby",
        AsyncMock(
            return_value=DiseaseRadarNearbyResponse(
                hotspots=[],
                queried_at=datetime.now(timezone.utc),
                radius_km=25.0,
            )
        ),
    )
    monkeypatch.setattr(
        "app.api.v1.voice.VoiceTranscriptionService.transcribe",
        AsyncMock(
            return_value=VoiceTranscribeResponse(
                transcript="Why is my crop stressed?",
                confidence=0.9,
                language="en",
            )
        ),
    )
    monkeypatch.setattr(
        "app.api.v1.localization.LocalizationService.get_labels",
        AsyncMock(
            return_value=LocalizationResponse(
                lang="en",
                labels={"dashboard.title": "HarvestIQ"},
            )
        ),
    )

    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client


def test_advisory_ask_api(client: TestClient) -> None:
    response = client.post(
        "/api/v1/advisory/ask",
        json={"farm_id": FARM_ID, "query": "Why is my wheat stressed?"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["synthesis"] == "Test synthesis"
    assert body["intelligence_snapshot_version"] == "v3"
    assert "explainability" in body


def test_disease_radar_nearby_api(client: TestClient) -> None:
    response = client.get(f"/api/v1/disease-radar/nearby?farm_id={FARM_ID}")
    assert response.status_code == 200
    assert "hotspots" in response.json()


def test_voice_transcribe_api(client: TestClient) -> None:
    response = client.post(
        "/api/v1/voice/transcribe",
        files={"audio": ("sample.webm", b"fake-audio", "audio/webm")},
    )
    assert response.status_code == 200
    assert response.json()["transcript"] == "Why is my crop stressed?"


def test_localization_api(client: TestClient) -> None:
    response = client.get("/api/v1/localization/en")
    assert response.status_code == 200
    assert response.json()["labels"]["dashboard.title"] == "HarvestIQ"
