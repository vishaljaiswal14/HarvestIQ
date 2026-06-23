from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from bson import ObjectId

from app.core.constants.weather import WeatherSource
from app.services.weather_service import WeatherService

FARM_ID = str(ObjectId())
USER_ID = str(ObjectId())


@pytest.mark.asyncio
async def test_cache_hit_skips_provider_call(monkeypatch) -> None:
    now = datetime.now(timezone.utc)
    db = MagicMock()
    db.weather_cache.find_one = AsyncMock(
        return_value={
            "current": {
                "temp": 30.0,
                "humidity": 50.0,
                "wind_speed": 10.0,
                "precipitation": 0.0,
            },
            "forecast": [
                {
                    "date": "2026-06-01",
                    "temp_min": 20.0,
                    "temp_max": 32.0,
                    "humidity": 55.0,
                    "precipitation": 0.0,
                    "wind_speed": 11.0,
                }
            ],
            "daily_gdd": [{"date": "2026-06-01", "gdd": 11.0}],
            "cached_at": now,
            "expires_at": now + timedelta(minutes=20),
        }
    )

    meteo_client = MagicMock()
    meteo_client.fetch_forecast = AsyncMock()

    async def fake_owned(_db, _farm_id, _user_id):
        return {
            "_id": ObjectId(FARM_ID),
            "user_id": ObjectId(USER_ID),
            "location": {"type": "Point", "coordinates": [75.8, 30.9]},
        }

    monkeypatch.setattr("app.services.weather_service.get_owned_farm", fake_owned)

    service = WeatherService(db, meteo_client=meteo_client)
    response = await service.get_forecast(FARM_ID, USER_ID, gdd_base_temp=10.0)

    assert response.source == WeatherSource.CACHE_HIT.value
    meteo_client.fetch_forecast.assert_not_called()
