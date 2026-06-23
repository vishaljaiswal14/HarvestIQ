import pytest
from fastapi import HTTPException
from unittest.mock import AsyncMock, MagicMock

from app.services.crop_stage_service import CropStageService


@pytest.mark.asyncio
async def test_unsupported_crop_returns_422() -> None:
    db = MagicMock()
    db.crop_characteristics.find_one = AsyncMock(return_value=None)
    service = CropStageService(db)

    with pytest.raises(HTTPException) as exc:
        await service._get_characteristics("UNKNOWN_CROP")

    assert exc.value.status_code == 422
