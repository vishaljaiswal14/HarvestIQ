from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.config import get_settings
from app.core.constants.disease import DISEASE_STATUS_CONFIRMED
from app.core.constants.radar import (
    RADAR_GRID_RESOLUTION,
    RISK_LEVEL_HIGH,
    RISK_LEVEL_LOW,
    RISK_LEVEL_MEDIUM,
)
from app.services.disease_radar_service import grid_key_from_coordinates, snap_coordinate


class DiseaseRadarAggregator:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self.db = db
        self.settings = get_settings()

    async def run(self) -> int:
        now = datetime.now(timezone.utc)
        window_start = now - timedelta(hours=self.settings.radar_window_hours)
        resolution = self.settings.radar_grid_resolution

        cursor = self.db.disease_reports.find(
            {
                "deterministic_status": DISEASE_STATUS_CONFIRMED,
                "created_at": {"$gte": window_start},
                "location": {"$exists": True},
            }
        )

        buckets: dict[tuple[str, str, str], dict[str, Any]] = defaultdict(
            lambda: {"case_count": 0, "lat_sum": 0.0, "lng_sum": 0.0}
        )

        async for report in cursor:
            coords = report["location"]["coordinates"]
            lng, lat = float(coords[0]), float(coords[1])
            disease_name = str(report.get("detected_disease", "UNKNOWN"))
            crop_type = str(report.get("crop_type", "UNKNOWN")).upper()
            key = grid_key_from_coordinates(lng, lat, resolution)
            bucket_key = (disease_name, crop_type, key)
            bucket = buckets[bucket_key]
            bucket["case_count"] += 1
            bucket["lat_sum"] += lat
            bucket["lng_sum"] += lng

        upserted = 0
        for (disease_name, crop_type, key), bucket in buckets.items():
            case_count = bucket["case_count"]
            avg_lat = bucket["lat_sum"] / case_count
            avg_lng = bucket["lng_sum"] / case_count
            snapped_lat = snap_coordinate(avg_lat, resolution)
            snapped_lng = snap_coordinate(avg_lng, resolution)
            risk_level = self._resolve_risk_level(case_count)

            await self.db.disease_radar.update_one(
                {
                    "disease_name": disease_name,
                    "grid_key": key,
                    "crop_type": crop_type,
                },
                {
                    "$set": {
                        "disease_name": disease_name,
                        "crop_type": crop_type,
                        "grid_key": key,
                        "location_grid": {
                            "type": "Point",
                            "coordinates": [snapped_lng, snapped_lat],
                        },
                        "case_count": case_count,
                        "risk_level": risk_level,
                        "last_updated": now,
                        "window_start": window_start,
                    }
                },
                upsert=True,
            )
            upserted += 1

        return upserted

    def _resolve_risk_level(self, case_count: int) -> str:
        if case_count >= self.settings.radar_min_cases_high:
            return RISK_LEVEL_HIGH
        if case_count >= self.settings.radar_min_cases_medium:
            return RISK_LEVEL_MEDIUM
        return RISK_LEVEL_LOW
