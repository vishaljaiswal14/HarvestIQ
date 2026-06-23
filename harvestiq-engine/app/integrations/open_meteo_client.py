from typing import Any, Optional

import httpx

from app.core.config import get_settings


class OpenMeteoClient:
    def __init__(self, client: Optional[httpx.AsyncClient] = None) -> None:
        self._client = client
        self._owns_client = client is None

    async def fetch_forecast(self, latitude: float, longitude: float) -> dict[str, Any]:
        settings = get_settings()
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "current": "temperature_2m,relative_humidity_2m,wind_speed_10m,precipitation",
            "daily": (
                "temperature_2m_max,temperature_2m_min,precipitation_sum,"
                "wind_speed_10m_max,relative_humidity_2m_mean"
            ),
            "timezone": "auto",
            "forecast_days": 7,
        }

        if self._client is None:
            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.get(settings.open_meteo_base_url, params=params)
        else:
            response = await self._client.get(settings.open_meteo_base_url, params=params)

        response.raise_for_status()
        return response.json()

    async def aclose(self) -> None:
        if self._owns_client and self._client is not None:
            await self._client.aclose()
