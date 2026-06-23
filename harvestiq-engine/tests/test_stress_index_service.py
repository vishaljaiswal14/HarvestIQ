from datetime import date, datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from bson import ObjectId
from fastapi import HTTPException

from app.models.engine_schemas import (
    CropCharacteristicsInDB,
    CropStageDefinition,
    DailyGddEntry,
    WeatherCurrent,
    WeatherForecastDay,
    WeatherForecastResponse,
)
from app.services.stress_index_service import FieldContext, StressIndexService

FARM_ID = str(ObjectId())
USER_ID = str(ObjectId())
CYCLE_ID = ObjectId()


def _characteristics() -> CropCharacteristicsInDB:
    return CropCharacteristicsInDB(
        _id=ObjectId(),
        crop_type="WHEAT",
        display_name="Wheat",
        gdd_base_temp=10.0,
        stages=[
            CropStageDefinition(name="Germination", gdd_min=0, gdd_max=100),
            CropStageDefinition(name="Tillering", gdd_min=100, gdd_max=400),
            CropStageDefinition(name="Flowering", gdd_min=400, gdd_max=800),
            CropStageDefinition(name="Maturity", gdd_min=800, gdd_max=1200),
        ],
        stage_vulnerability={
            "Germination": 0.50,
            "Tillering": 0.60,
            "Flowering": 0.85,
            "Maturity": 0.30,
        },
    )


def _hot_weather() -> WeatherForecastResponse:
    now = datetime.now(timezone.utc)
    forecast = [
        WeatherForecastDay(
            date=date(2026, 6, day),
            temp_min=35.0,
            temp_max=41.0,
            humidity=30.0,
            precipitation=0.0,
            wind_speed=10.0,
        )
        for day in range(1, 8)
    ]
    return WeatherForecastResponse(
        farm_id=FARM_ID,
        current=WeatherCurrent(temp=41.0, humidity=30.0, wind_speed=10.0, precipitation=0.0),
        forecast=forecast,
        daily_gdd=[DailyGddEntry(date=day.date, gdd=15.0) for day in forecast],
        source="CACHE_HIT",
        cached_at=now,
    )


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

    monkeypatch.setattr("app.services.stress_index_service.get_owned_farm", fake_owned)

    service = StressIndexService(db)
    with pytest.raises(HTTPException) as exc:
        await service.compute(FARM_ID, USER_ID)
    assert exc.value.status_code == 422


@pytest.mark.asyncio
async def test_high_temperature_produces_high_stress(monkeypatch) -> None:
    db = MagicMock()
    db.crop_cycles.find_one = AsyncMock(
        return_value={
            "_id": CYCLE_ID,
            "farm_id": ObjectId(FARM_ID),
            "crop_type": "WHEAT",
            "sowing_date": datetime(2026, 1, 1, tzinfo=timezone.utc),
            "status": "ACTIVE",
        }
    )
    db.crop_characteristics.find_one = AsyncMock(return_value=_characteristics().model_dump(by_alias=True))
    db.stress_logs.find_one = AsyncMock(return_value=None)
    db.stress_logs.insert_one = AsyncMock()

    async def fake_owned(_db, _farm_id, _user_id):
        return {
            "_id": ObjectId(FARM_ID),
            "user_id": ObjectId(USER_ID),
            "location": {"type": "Point", "coordinates": [77.5, 27.2]},
        }

    monkeypatch.setattr("app.services.stress_index_service.get_owned_farm", fake_owned)

    service = StressIndexService(db)
    service.weather_service.get_forecast = AsyncMock(return_value=_hot_weather())

    result = await service.compute(FARM_ID, USER_ID)

    assert result.fsi >= 0.67
    assert result.classification == "HIGH_STRESS"
    assert result.explanation.summary
    assert result.explanation.primary_factor
    db.stress_logs.insert_one.assert_called_once()


@pytest.mark.asyncio
async def test_stress_log_skipped_when_classification_unchanged(monkeypatch) -> None:
    db = MagicMock()
    db.crop_cycles.find_one = AsyncMock(
        return_value={
            "_id": CYCLE_ID,
            "farm_id": ObjectId(FARM_ID),
            "crop_type": "WHEAT",
            "sowing_date": datetime(2026, 1, 1, tzinfo=timezone.utc),
            "status": "ACTIVE",
        }
    )
    db.crop_characteristics.find_one = AsyncMock(return_value=_characteristics().model_dump(by_alias=True))
    db.stress_logs.find_one = AsyncMock(
        return_value={
            "classification": "HIGH_STRESS",
            "fsi_score": 0.74,
            "calculated_at": datetime.now(timezone.utc) - timedelta(minutes=5),
        }
    )
    db.stress_logs.insert_one = AsyncMock()

    async def fake_owned(_db, _farm_id, _user_id):
        return {
            "_id": ObjectId(FARM_ID),
            "user_id": ObjectId(USER_ID),
            "location": {"type": "Point", "coordinates": [77.5, 27.2]},
        }

    monkeypatch.setattr("app.services.stress_index_service.get_owned_farm", fake_owned)

    service = StressIndexService(db)
    service.weather_service.get_forecast = AsyncMock(return_value=_hot_weather())

    await service.compute(FARM_ID, USER_ID)
    db.stress_logs.insert_one.assert_not_called()


def test_calculate_fsi_from_context_returns_explanation() -> None:
    service = StressIndexService(MagicMock())
    context = FieldContext(
        farm={"_id": ObjectId(FARM_ID)},
        cycle={"_id": CYCLE_ID, "crop_type": "WHEAT"},
        characteristics=_characteristics(),
        weather=_hot_weather(),
        stage_name="Tillering",
        current_gdd=200.0,
        current_stage_def=CropStageDefinition(name="Tillering", gdd_min=100, gdd_max=400),
    )
    result = service.calculate_fsi_from_context(context)
    assert result.explanation.inputs["current_temp"] == 41.0
