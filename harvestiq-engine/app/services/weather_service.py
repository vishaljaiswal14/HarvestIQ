from datetime import date, datetime, timedelta, timezone
from typing import Any, Optional

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.config import get_settings
from app.core.constants.crop_types import normalize_crop_type
from app.core.constants.weather import WeatherSource
from app.core.exceptions import bad_gateway, unprocessable_entity
from app.integrations.open_meteo_client import OpenMeteoClient
from app.models.engine_schemas import (
    DailyGddEntry,
    WeatherCurrent,
    WeatherForecastDay,
    WeatherForecastResponse,
)
from app.services.deterministic_engine import calculate_daily_gdd
from app.services.farm_access_service import get_owned_farm


class WeatherService:
    def __init__(
        self,
        db: AsyncIOMotorDatabase,
        meteo_client: Optional[OpenMeteoClient] = None,
    ) -> None:
        self.db = db
        self.meteo_client = meteo_client or OpenMeteoClient()
        self.settings = get_settings()

    async def get_forecast(
        self,
        farm_id: str,
        user_id: str,
        gdd_base_temp: float = 10.0,
    ) -> WeatherForecastResponse:
        farm = await get_owned_farm(self.db, farm_id, user_id)
        now = datetime.now(timezone.utc)

        cached = await self.db.weather_cache.find_one(
            {
                "farm_id": ObjectId(farm_id),
                "expires_at": {"$gt": now},
            }
        )
        if cached is not None:
            return self._to_response(farm_id, cached, WeatherSource.CACHE_HIT.value)

        try:
            longitude, latitude = farm["location"]["coordinates"]
            raw = await self.meteo_client.fetch_forecast(latitude, longitude)
        except Exception as exc:
            raise bad_gateway(f"Weather provider unavailable: {exc}") from exc

        parsed = self._parse_open_meteo(raw, gdd_base_temp)
        expires_at = now + timedelta(minutes=self.settings.weather_cache_ttl_minutes)

        cache_doc = {
            "farm_id": ObjectId(farm_id),
            "location": farm["location"],
            "current": parsed["current"],
            "forecast": parsed["forecast"],
            "daily_gdd": parsed["daily_gdd"],
            "source": WeatherSource.OPEN_METEO.value,
            "cached_at": now,
            "expires_at": expires_at,
        }

        await self.db.weather_cache.update_one(
            {"farm_id": ObjectId(farm_id)},
            {"$set": cache_doc},
            upsert=True,
        )

        cache_doc["cached_at"] = now
        return self._to_response(farm_id, cache_doc, WeatherSource.OPEN_METEO.value)

    async def get_gdd_base_for_farm(self, farm_id: str) -> float:
        from app.services.farm_access_service import get_latest_relevant_crop_cycle
        try:
            cycle, cycle_status = await get_latest_relevant_crop_cycle(self.db, farm_id)
        except Exception:
            return 10.0


        crop_type = normalize_crop_type(cycle["crop_type"])
        characteristics = await self.db.crop_characteristics.find_one({"crop_type": crop_type})
        if characteristics is None:
            raise unprocessable_entity(f"Unsupported crop type: {cycle['crop_type']}")
        return float(characteristics["gdd_base_temp"])

    def _parse_open_meteo(self, raw: dict[str, Any], base_temp: float) -> dict[str, Any]:
        current = raw.get("current", {})
        daily = raw.get("daily", {})
        dates = daily.get("time", [])
        temp_max = daily.get("temperature_2m_max", [])
        temp_min = daily.get("temperature_2m_min", [])
        precipitation = daily.get("precipitation_sum", [])
        wind_speed = daily.get("wind_speed_10m_max", [])
        humidity = daily.get("relative_humidity_2m_mean", [])

        forecast_days: list[dict[str, Any]] = []
        daily_gdd: list[dict[str, Any]] = []

        for index, day_str in enumerate(dates):
            day = date.fromisoformat(day_str)
            t_max = float(temp_max[index]) if index < len(temp_max) else 0.0
            t_min = float(temp_min[index]) if index < len(temp_min) else 0.0
            forecast_days.append(
                {
                    "date": day.isoformat(),
                    "temp_min": t_min,
                    "temp_max": t_max,
                    "humidity": float(humidity[index]) if index < len(humidity) else 0.0,
                    "precipitation": float(precipitation[index]) if index < len(precipitation) else 0.0,
                    "wind_speed": float(wind_speed[index]) if index < len(wind_speed) else 0.0,
                }
            )
            daily_gdd.append(
                {
                    "date": day.isoformat(),
                    "gdd": calculate_daily_gdd(t_min, t_max, base_temp),
                }
            )

        return {
            "current": {
                "temp": float(current.get("temperature_2m", 0.0)),
                "humidity": float(current.get("relative_humidity_2m", 0.0)),
                "wind_speed": float(current.get("wind_speed_10m", 0.0)),
                "precipitation": float(current.get("precipitation", 0.0)),
            },
            "forecast": forecast_days,
            "daily_gdd": daily_gdd,
        }

    def _to_response(
        self,
        farm_id: str,
        doc: dict[str, Any],
        source: str,
    ) -> WeatherForecastResponse:
        cached_at = doc["cached_at"]
        if isinstance(cached_at, datetime) and cached_at.tzinfo is None:
            cached_at = cached_at.replace(tzinfo=timezone.utc)

        return WeatherForecastResponse(
            farm_id=farm_id,
            current=WeatherCurrent(**doc["current"]),
            forecast=[
                WeatherForecastDay(
                    date=date.fromisoformat(item["date"])
                    if isinstance(item["date"], str)
                    else item["date"],
                    temp_min=item["temp_min"],
                    temp_max=item["temp_max"],
                    humidity=item["humidity"],
                    precipitation=item["precipitation"],
                    wind_speed=item["wind_speed"],
                )
                for item in doc["forecast"]
            ],
            daily_gdd=[
                DailyGddEntry(
                    date=date.fromisoformat(item["date"])
                    if isinstance(item["date"], str)
                    else item["date"],
                    gdd=item["gdd"],
                )
                for item in doc.get("daily_gdd", [])
            ],
            source=source,
            cached_at=cached_at,
        )
