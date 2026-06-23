from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.api.deps import get_current_user
from app.core.database import get_database
from app.models.day5_schemas import DiseaseRadarNearbyResponse
from app.services.disease_radar_service import DiseaseRadarService

router = APIRouter(prefix="/disease-radar", tags=["disease-radar"])


@router.get("/nearby", response_model=DiseaseRadarNearbyResponse)
async def get_nearby_disease_radar(
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncIOMotorDatabase, Depends(get_database)],
    farm_id: Annotated[Optional[str], Query()] = None,
    lat: Annotated[Optional[float], Query()] = None,
    lng: Annotated[Optional[float], Query()] = None,
    radius_km: Annotated[Optional[float], Query(ge=1, le=100)] = None,
    crop_type: Annotated[Optional[str], Query()] = None,
) -> DiseaseRadarNearbyResponse:
    service = DiseaseRadarService(db)
    return await service.nearby(
        user_id=str(current_user["_id"]),
        farm_id=farm_id,
        lat=lat,
        lng=lng,
        radius_km=radius_km,
        crop_type=crop_type,
    )
