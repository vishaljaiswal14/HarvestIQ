from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.constants.disease import DISEASE_STATUS_CONFIRMED
from app.services.disease_radar_aggregator import DiseaseRadarAggregator


@pytest.mark.asyncio
async def test_aggregator_query_filters_confirmed_only() -> None:
    db = MagicMock()

    async def fake_cursor():
        if False:
            yield {}

    db.disease_reports.find = MagicMock(return_value=fake_cursor())
    db.disease_radar.update_one = AsyncMock()

    aggregator = DiseaseRadarAggregator(db)
    await aggregator.run()

    query = db.disease_reports.find.call_args[0][0]
    assert query["deterministic_status"] == DISEASE_STATUS_CONFIRMED


@pytest.mark.asyncio
async def test_aggregator_risk_level_high_for_many_cases() -> None:
    now = datetime.now(timezone.utc)
    reports = [
        {
            "detected_disease": "WHEAT_RUST",
            "crop_type": "WHEAT",
            "deterministic_status": DISEASE_STATUS_CONFIRMED,
            "created_at": now,
            "location": {"type": "Point", "coordinates": [77.50, 27.20]},
        }
        for _ in range(6)
    ]

    async def fake_cursor():
        for report in reports:
            yield report

    db = MagicMock()
    db.disease_reports.find = MagicMock(return_value=fake_cursor())
    db.disease_radar.update_one = AsyncMock()

    aggregator = DiseaseRadarAggregator(db)
    await aggregator.run()

    saved = db.disease_radar.update_one.call_args[0][1]["$set"]
    assert saved["case_count"] == 6
    assert saved["risk_level"] == "HIGH"
