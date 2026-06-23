from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from bson import ObjectId

from app.services.weather_service import WeatherService

FARM_ID = str(ObjectId())
USER_ID = str(ObjectId())


@pytest.mark.asyncio
async def test_expired_cache_triggers_provider_fetch(monkeypatch) -> None:
    db = MagicMock()
    db.weather_cache.find_one = AsyncMock(return_value=None)
    db.weather_cache.update_one = AsyncMock()

    meteo_client = MagicMock()
    meteo_client.fetch_forecast = AsyncMock(
        return_value={
            "current": {
                "temperature_2m": 30.0,
                "relative_humidity_2m": 50.0,
                "wind_speed_10m": 10.0,
                "precipitation": 0.0,
            },
            "daily": {
                "time": ["2026-06-01"],
                "temperature_2m_max": [32.0],
                "temperature_2m_min": [20.0],
                "precipitation_sum": [0.0],
                "wind_speed_10m_max": [11.0],
                "relative_humidity_2m_mean": [55.0],
            },
        }
    )

    async def fake_owned(_db, _farm_id, _user_id):
        return {
            "_id": ObjectId(FARM_ID),
            "user_id": ObjectId(USER_ID),
            "location": {"type": "Point", "coordinates": [75.8, 30.9]},
        }

    monkeypatch.setattr("app.services.weather_service.get_owned_farm", fake_owned)

    service = WeatherService(db, meteo_client=meteo_client)
    response = await service.get_forecast(FARM_ID, USER_ID, gdd_base_temp=10.0)

    meteo_client.fetch_forecast.assert_called_once()
    db.weather_cache.update_one.assert_called_once()
    assert response.source == "open-meteo"

    upsert_call = db.weather_cache.update_one.call_args
    cache_doc = upsert_call.args[1]["$set"]
    expires_at = cache_doc["expires_at"]
    cached_at = cache_doc["cached_at"]
    assert expires_at > cached_at
    delta = expires_at - cached_at
    assert 29 <= delta.total_seconds() / 60 <= 31
