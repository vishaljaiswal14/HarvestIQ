from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_current_user
from app.core.database import get_database
from app.models.engine_schemas import WeatherForecastResponse
from app.services.weather_service import WeatherService

router = APIRouter(prefix="/weather", tags=["weather"])


@router.get("/forecast", response_model=WeatherForecastResponse)
async def get_weather_forecast(
    farm_id: Annotated[str, Query(...)],
    current_user: Annotated[dict, Depends(get_current_user)],
) -> WeatherForecastResponse:
    db = get_database()
    service = WeatherService(db)
    base_temp = await service.get_gdd_base_for_farm(farm_id)
    return await service.get_forecast(farm_id, str(current_user["_id"]), gdd_base_temp=base_temp)
