from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from bson import ObjectId
from fastapi.testclient import TestClient

from app.api.deps import get_current_user
from app.core.database import get_database
from app.main import create_app
from app.models.day4_schemas import SoilRecordResponse, NutrientDeficiencyStatus
from app.models.engine_schemas import ExplanationPayload

USER_ID = str(ObjectId())
FARM_ID = str(ObjectId())

@pytest.fixture
def client(monkeypatch) -> TestClient:
    monkeypatch.setattr("app.main.connect_to_mongo", AsyncMock())
    monkeypatch.setattr("app.main.ensure_indexes", AsyncMock())
    monkeypatch.setattr("app.main.close_mongo_connection", AsyncMock())

    app = create_app()

    async def fake_user():
        return {"_id": ObjectId(USER_ID), "preferred_lang": "hi", "role": "FARMER"}

    app.dependency_overrides[get_current_user] = fake_user
    app.dependency_overrides[get_database] = lambda: MagicMock()

    now = datetime.now(timezone.utc)
    explanation = ExplanationPayload(
        summary="Soil health index is optimal",
        inputs={},
        primary_factor="NITROGEN",
    )

    mock_response = SoilRecordResponse(
        id=str(ObjectId()),
        farm_id=FARM_ID,
        crop_type="WHEAT",
        nitrogen=80.0,
        phosphorus=18.0,
        potassium=220.0,
        ph=6.8,
        organic_carbon=0.55,
        electrical_conductivity=0.8,
        deficiency_status=NutrientDeficiencyStatus(
            nitrogen="OPTIMAL",
            phosphorus="OPTIMAL",
            potassium="OPTIMAL",
            ph="OPTIMAL",
            organic_carbon="OPTIMAL",
            electrical_conductivity="OPTIMAL",
        ),
        soil_health_index=90.0,
        explanation=explanation,
        recorded_at=now,
    )

    monkeypatch.setattr(
        "app.services.soil_health_service.SoilHealthService.create_record",
        AsyncMock(return_value=mock_response),
    )
    monkeypatch.setattr(
        "app.services.soil_health_service.SoilHealthService.get_latest",
        AsyncMock(return_value=mock_response),
    )

    return TestClient(app)


def test_create_soil_record_endpoint(client: TestClient) -> None:
    response = client.post(
        "/api/v1/soil/records",
        json={
            "farm_id": FARM_ID,
            "nitrogen": 80,
            "phosphorus": 18,
            "potassium": 220,
            "ph": 6.8,
            "organic_carbon": 0.55,
            "electrical_conductivity": 0.8,
        },
    )
    assert response.status_code == 201
    assert response.json()["farm_id"] == FARM_ID
    assert response.json()["soil_health_index"] == 90.0


def test_get_latest_soil_record_endpoint(client: TestClient) -> None:
    response = client.get(f"/api/v1/soil/records/latest?farm_id={FARM_ID}")
    assert response.status_code == 200
    assert response.json()["farm_id"] == FARM_ID
