from unittest.mock import AsyncMock, MagicMock

import pytest
from bson import ObjectId
from fastapi import HTTPException

from app.services.farm_access_service import get_owned_farm


@pytest.mark.asyncio
async def test_missing_location_returns_422() -> None:
    farm_id = str(ObjectId())
    user_id = str(ObjectId())
    db = MagicMock()
    db.farms.find_one = AsyncMock(
        return_value={
            "_id": ObjectId(farm_id),
            "user_id": ObjectId(user_id),
            "location": None,
        }
    )

    with pytest.raises(HTTPException) as exc:
        await get_owned_farm(db, farm_id, user_id)

    assert exc.value.status_code == 422
    assert "Farm location missing" in exc.value.detail


@pytest.mark.asyncio
async def test_ownership_violation_returns_403() -> None:
    farm_id = str(ObjectId())
    user_id = str(ObjectId())
    db = MagicMock()
    db.farms.find_one = AsyncMock(
        return_value={
            "_id": ObjectId(farm_id),
            "user_id": ObjectId(),
            "location": {"type": "Point", "coordinates": [75.8, 30.9]},
        }
    )

    with pytest.raises(HTTPException) as exc:
        await get_owned_farm(db, farm_id, user_id)

    assert exc.value.status_code == 403
