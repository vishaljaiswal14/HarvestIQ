from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from bson import ObjectId
from fastapi.testclient import TestClient

from app.api.deps import get_current_user
from app.core.database import get_database
from app.main import create_app
from app.models.knowledge_schemas import KnowledgeSyncResponse, LocalCropSchema

USER_ID = str(ObjectId())


@pytest.fixture
def client(monkeypatch) -> TestClient:
    monkeypatch.setattr("app.main.connect_to_mongo", AsyncMock())
    monkeypatch.setattr("app.main.ensure_indexes", AsyncMock())
    monkeypatch.setattr("app.main.close_mongo_connection", AsyncMock())

    app = create_app()

    async def fake_user():
        return {"_id": ObjectId(USER_ID), "preferred_lang": "hi", "role": "FARMER"}

    # Set up mock database characteristics search
    fake_crop = {
        "crop_type": "WHEAT",
        "display_name": "Wheat",
        "gdd_base_temp": 10.0,
        "stages": [
            {"name": "Germination", "gdd_min": 0, "gdd_max": 100},
            {"name": "Flowering", "gdd_min": 400, "gdd_max": 800},
        ],
        "stage_vulnerability": {
            "Germination": 0.5,
            "Flowering": 0.85
        }
    }

    mock_db = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.find = MagicMock(return_value=mock_cursor)
    
    # Mocking async iterator for motor cursor
    async def fake_async_iter(*args, **kwargs):
        yield fake_crop

    mock_cursor.__aiter__ = fake_async_iter

    mock_db.crop_characteristics = mock_cursor

    app.dependency_overrides[get_current_user] = fake_user
    app.dependency_overrides[get_database] = lambda: mock_db

    return TestClient(app)


def test_knowledge_sync_endpoint(client: TestClient) -> None:
    response = client.get("/api/v1/knowledge/sync")
    assert response.status_code == 200
    
    data = response.json()
    assert "timestamp" in data
    assert "crops" in data
    assert "stages" in data
    assert "diseases" in data
    assert "calendars" in data

    # Verify WHEAT crop parsing
    wheat = [c for c in data["crops"] if c["crop_type"] == "WHEAT"][0]
    assert wheat["display_name"] == "Wheat"
    assert wheat["gdd_base_temp"] == 10.0
    assert wheat["nitrogen_rdf"] == 120.0

    # Verify stages
    germination = [s for s in data["stages"] if s["stage_name"] == "Germination"][0]
    assert germination["crop_type"] == "WHEAT"
    assert germination["gdd_min"] == 0
    assert germination["gdd_max"] == 100
    assert germination["vulnerability"] == 0.5
