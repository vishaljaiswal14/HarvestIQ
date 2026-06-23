from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.localization_service import LocalizationService


@pytest.mark.asyncio
async def test_get_labels_returns_dictionary() -> None:
    db = MagicMock()

    async def fake_cursor():
        yield {"key": "dashboard.title", "value": "HarvestIQ"}
        yield {"key": "dashboard.advisory", "value": "Ask Advisory"}

    db.localization_dictionary.find = MagicMock(return_value=fake_cursor())

    service = LocalizationService(db)
    result = await service.get_labels("en")

    assert result.lang == "en"
    assert result.labels["dashboard.title"] == "HarvestIQ"


@pytest.mark.asyncio
async def test_get_labels_falls_back_to_english() -> None:
    db = MagicMock()

    async def empty_cursor():
        if False:
            yield {}

    async def english_cursor():
        yield {"key": "dashboard.title", "value": "HarvestIQ"}

    db.localization_dictionary.find = MagicMock(side_effect=[empty_cursor(), english_cursor()])

    service = LocalizationService(db)
    result = await service.get_labels("mr")

    assert result.labels["dashboard.title"] == "HarvestIQ"
