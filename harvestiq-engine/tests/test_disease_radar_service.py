from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from bson import ObjectId

from app.services.disease_radar_service import DiseaseRadarService, grid_key_from_coordinates, haversine_km


FARM_ID = str(ObjectId())
USER_ID = str(ObjectId())


def test_grid_key_snaps_coordinates() -> None:
    assert grid_key_from_coordinates(77.52, 27.23, 0.05) == "27.25,77.50"


def test_haversine_distance() -> None:
    distance = haversine_km(77.5, 27.2, 77.6, 27.3)
    assert 10 < distance < 20


@pytest.mark.asyncio
async def test_nearby_filters_by_radius(monkeypatch) -> None:
    db = MagicMock()

    async def fake_cursor():
        now = datetime.now(timezone.utc)
        yield {
            "disease_name": "WHEAT_RUST",
            "crop_type": "WHEAT",
            "risk_level": "HIGH",
            "case_count": 8,
            "location_grid": {"type": "Point", "coordinates": [77.51, 27.21]},
            "last_updated": now,
        }
        yield {
            "disease_name": "WHEAT_RUST",
            "crop_type": "WHEAT",
            "risk_level": "LOW",
            "case_count": 1,
            "location_grid": {"type": "Point", "coordinates": [80.0, 30.0]},
            "last_updated": now,
        }

    db.disease_radar.find = MagicMock(return_value=fake_cursor())

    async def fake_owned(_db, _farm_id, _user_id):
        return {
            "_id": ObjectId(FARM_ID),
            "location": {"type": "Point", "coordinates": [77.5, 27.2]},
        }

    monkeypatch.setattr("app.services.disease_radar_service.get_owned_farm", fake_owned)

    service = DiseaseRadarService(db)
    result = await service.nearby(user_id=USER_ID, farm_id=FARM_ID, radius_km=25.0)

    assert len(result.hotspots) == 1
    assert result.hotspots[0].disease_name == "WHEAT_RUST"
