from unittest.mock import AsyncMock, MagicMock

import pytest
from bson import ObjectId
from fastapi import HTTPException

from app.models.day4_schemas import SoilRecordCreateSchema
from app.services.soil_health_service import SoilHealthService

FARM_ID = str(ObjectId())
USER_ID = str(ObjectId())
CYCLE_ID = ObjectId()


@pytest.mark.asyncio
async def test_create_soil_record_persists(monkeypatch) -> None:
    db = MagicMock()
    db.crop_cycles.find_one = AsyncMock(
        return_value={
            "_id": CYCLE_ID,
            "farm_id": ObjectId(FARM_ID),
            "crop_type": "WHEAT",
            "status": "ACTIVE",
        }
    )
    db.soil_records.insert_one = AsyncMock(return_value=MagicMock(inserted_id=ObjectId()))

    async def fake_owned(_db, _farm_id, _user_id):
        return {
            "_id": ObjectId(FARM_ID),
            "user_id": ObjectId(USER_ID),
            "state": "Rajasthan",
            "district": "Bharatpur",
            "location": {"type": "Point", "coordinates": [77.5, 27.2]},
        }

    monkeypatch.setattr("app.services.soil_health_service.get_owned_farm", fake_owned)

    service = SoilHealthService(db)
    result = await service.create_record(
        USER_ID,
        SoilRecordCreateSchema(
            farm_id=FARM_ID,
            nitrogen=80,
            phosphorus=18,
            potassium=220,
            ph=6.8,
            organic_carbon=0.55,
            electrical_conductivity=0.8,
        ),
    )

    assert result.crop_type == "WHEAT"
    assert result.deficiency_status.nitrogen == "LOW"
    assert result.soil_health_index < 0.9
    assert result.explanation.summary
    db.soil_records.insert_one.assert_called_once()


@pytest.mark.asyncio
async def test_missing_crop_cycle_returns_422(monkeypatch) -> None:
    db = MagicMock()
    db.crop_cycles.find_one = AsyncMock(return_value=None)

    async def fake_owned(_db, _farm_id, _user_id):
        return {
            "_id": ObjectId(FARM_ID),
            "user_id": ObjectId(USER_ID),
            "location": {"type": "Point", "coordinates": [77.5, 27.2]},
        }

    monkeypatch.setattr("app.services.soil_health_service.get_owned_farm", fake_owned)

    service = SoilHealthService(db)
    with pytest.raises(HTTPException) as exc:
        await service.create_record(
            USER_ID,
            SoilRecordCreateSchema(
                farm_id=FARM_ID,
                nitrogen=80,
                phosphorus=18,
                potassium=220,
                ph=6.8,
                organic_carbon=0.55,
                electrical_conductivity=0.8,
            ),
        )
    assert exc.value.status_code == 422
