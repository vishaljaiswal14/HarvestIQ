import math
from datetime import datetime, timezone
from typing import Any, Optional

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.config import get_settings
from app.core.constants.radar import RADAR_DEFAULT_RADIUS_KM
from app.core.exceptions import not_found, unprocessable_entity
from app.models.day5_schemas import DiseaseRadarHotspot, DiseaseRadarNearbyResponse
from app.services.farm_access_service import get_owned_farm


def snap_coordinate(value: float, resolution: float) -> float:
    return round(value / resolution) * resolution


def grid_key_from_coordinates(lng: float, lat: float, resolution: float) -> str:
    snapped_lat = snap_coordinate(lat, resolution)
    snapped_lng = snap_coordinate(lng, resolution)
    return f"{snapped_lat:.2f},{snapped_lng:.2f}"


def haversine_km(lng1: float, lat1: float, lng2: float, lat2: float) -> float:
    radius_earth_km = 6371.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lng2 - lng1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    return 2 * radius_earth_km * math.atan2(math.sqrt(a), math.sqrt(1 - a))


class DiseaseRadarService:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self.db = db
        self.settings = get_settings()

    async def nearby(
        self,
        user_id: str,
        farm_id: Optional[str] = None,
        lat: Optional[float] = None,
        lng: Optional[float] = None,
        radius_km: Optional[float] = None,
        crop_type: Optional[str] = None,
    ) -> DiseaseRadarNearbyResponse:
        if farm_id:
            farm = await get_owned_farm(self.db, farm_id, user_id)
            coordinates = farm["location"]["coordinates"]
            origin_lng, origin_lat = float(coordinates[0]), float(coordinates[1])
        elif lat is not None and lng is not None:
            origin_lat, origin_lng = lat, lng
        else:
            raise unprocessable_entity("farm_id or lat/lng coordinates are required")

        search_radius = radius_km or RADAR_DEFAULT_RADIUS_KM
        query: dict[str, Any] = {}
        if crop_type:
            query["crop_type"] = crop_type.upper()

        cursor = self.db.disease_radar.find(query)
        hotspots: list[DiseaseRadarHotspot] = []
        now = datetime.now(timezone.utc)

        async for doc in cursor:
            grid_coords = doc["location_grid"]["coordinates"]
            grid_lng, grid_lat = float(grid_coords[0]), float(grid_coords[1])
            distance = haversine_km(origin_lng, origin_lat, grid_lng, grid_lat)
            if distance > search_radius:
                continue
            hotspots.append(
                DiseaseRadarHotspot(
                    disease_name=doc["disease_name"],
                    crop_type=doc.get("crop_type", ""),
                    risk_level=doc["risk_level"],
                    case_count=int(doc["case_count"]),
                    distance_km=round(distance, 2),
                    location_grid=doc["location_grid"],
                    last_updated=doc["last_updated"],
                )
            )

        hotspots.sort(key=lambda item: (item.risk_level, -item.case_count, item.distance_km))
        return DiseaseRadarNearbyResponse(
            hotspots=hotspots,
            queried_at=now,
            radius_km=search_radius,
        )

    async def get_by_id(self, radar_id: str) -> dict:
        if not ObjectId.is_valid(radar_id):
            raise not_found("Radar entry not found")
        doc = await self.db.disease_radar.find_one({"_id": ObjectId(radar_id)})
        if doc is None:
            raise not_found("Radar entry not found")
        return doc
