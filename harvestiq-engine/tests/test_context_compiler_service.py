from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from bson import ObjectId

from app.models.day4_schemas import KnowledgeChunkResult
from app.models.day5_schemas import DiseaseRadarHotspot, DiseaseRadarNearbyResponse
from app.models.engine_schemas import (
    CropCharacteristicsInDB,
    CropStageDefinition,
    FsiComponents,
    StressIndexResponse,
    WeatherCurrent,
    WeatherForecastDay,
    WeatherForecastResponse,
)
from app.services.context_compiler_service import ContextCompilerService
from app.services.stress_index_service import FieldContext


FARM_ID = str(ObjectId())
USER_ID = str(ObjectId())


class MockAsyncCursor:
    def __init__(self, items: list) -> None:
        self._items = items

    def sort(self, *_args, **_kwargs):
        return self

    def limit(self, *_args, **_kwargs):
        return self

    def __aiter__(self):
        self._index = 0
        return self

    async def __anext__(self):
        if self._index >= len(self._items):
            raise StopAsyncIteration
        item = self._items[self._index]
        self._index += 1
        return item


def _stress_response() -> StressIndexResponse:
    now = datetime.now(timezone.utc)
    return StressIndexResponse(
        farm_id=FARM_ID,
        crop_cycle_id=str(ObjectId()),
        crop_type="WHEAT",
        stage="Tillering",
        fsi=0.82,
        classification="HIGH_STRESS",
        primary_factor="THERMAL",
        components=FsiComponents(temp_stress=0.9, rainfall_deficit=0.4, gdd_scale=0.5),
        calculated_at=now,
        explanation={
            "summary": "FSI is 0.82 (High Stress) primarily due to thermal stress.",
            "inputs": {"current_temp": 39.0},
            "primary_factor": "THERMAL",
        },
    )


def _field_context() -> FieldContext:
    characteristics = CropCharacteristicsInDB(
        _id=ObjectId(),
        crop_type="WHEAT",
        display_name="Wheat",
        gdd_base_temp=5.0,
        stages=[CropStageDefinition(name="Tillering", gdd_min=0, gdd_max=500)],
        stage_vulnerability={"Tillering": 0.6},
    )
    weather = WeatherForecastResponse(
        farm_id=FARM_ID,
        current=WeatherCurrent(temp=39.0, humidity=40.0, wind_speed=8.0, precipitation=0.0),
        forecast=[
            WeatherForecastDay(
                date=datetime.now(timezone.utc).date(),
                temp_min=28.0,
                temp_max=40.0,
                humidity=35.0,
                precipitation=0.0,
                wind_speed=10.0,
            )
        ],
        daily_gdd=[],
        source="open-meteo",
        cached_at=datetime.now(timezone.utc),
    )
    return FieldContext(
        farm={
            "_id": ObjectId(FARM_ID),
            "name": "Test Farm",
            "state": "Rajasthan",
            "district": "Bharatpur",
            "location": {"type": "Point", "coordinates": [77.5, 27.2]},
        },
        cycle={"_id": ObjectId(), "crop_type": "WHEAT"},
        characteristics=characteristics,
        weather=weather,
        stage_name="Tillering",
        current_gdd=220.0,
        current_stage_def=characteristics.stages[0],
    )


@pytest.mark.asyncio
async def test_compile_context_includes_snapshot_version(monkeypatch) -> None:
    db = MagicMock()

    db.soil_records.find_one = AsyncMock(return_value=None)
    db.alerts.find = MagicMock(return_value=MockAsyncCursor([]))
    db.alerts.count_documents = AsyncMock(return_value=0)
    db.disease_reports.find = MagicMock(return_value=MockAsyncCursor([]))
    db.disease_reports.find_one = AsyncMock(return_value=None)
    db.stress_logs.find = MagicMock(return_value=MockAsyncCursor([]))

    service = ContextCompilerService(db)
    monkeypatch.setattr(service.stress_service, "build_field_context", AsyncMock(return_value=_field_context()))
    monkeypatch.setattr(
        service.stress_service,
        "calculate_fsi_from_context",
        MagicMock(return_value=_stress_response()),
    )
    monkeypatch.setattr(service.rag_service, "hybrid_search", AsyncMock(return_value=[]))
    monkeypatch.setattr(
        service.radar_service,
        "nearby",
        AsyncMock(
            return_value=DiseaseRadarNearbyResponse(
                hotspots=[],
                queried_at=datetime.now(timezone.utc),
                radius_km=25.0,
            )
        ),
    )

    result = await service.compile_context(USER_ID, FARM_ID, "Why is my wheat stressed?", "hi")

    assert result.intelligence_snapshot_version == "v3"
    assert "snapshot_version: v3" in result.context_package
    assert "## Stress Momentum" in result.context_package
    assert "## Yield Risk" in result.context_package
    assert result.mitigation_locked is True
    assert result.context_hash
    assert "THERMAL" in result.explainability["primary_factor"]


@pytest.mark.asyncio
async def test_compile_context_includes_rag_citations(monkeypatch) -> None:
    db = MagicMock()

    db.soil_records.find_one = AsyncMock(return_value=None)
    db.alerts.find = MagicMock(return_value=MockAsyncCursor([]))
    db.alerts.count_documents = AsyncMock(return_value=0)
    db.disease_reports.find = MagicMock(return_value=MockAsyncCursor([]))
    db.disease_reports.find_one = AsyncMock(return_value=None)
    db.stress_logs.find = MagicMock(return_value=MockAsyncCursor([]))

    service = ContextCompilerService(db)
    monkeypatch.setattr(service.stress_service, "build_field_context", AsyncMock(return_value=_field_context()))
    monkeypatch.setattr(
        service.stress_service,
        "calculate_fsi_from_context",
        MagicMock(return_value=_stress_response()),
    )
    monkeypatch.setattr(
        service.rag_service,
        "hybrid_search",
        AsyncMock(
            return_value=[
                KnowledgeChunkResult(
                    text="Wheat heat stress management in Rajasthan.",
                    source="ICAR",
                    score=0.84,
                    metadata={
                        "source_document": "icar-wheat-heat-stress-rajasthan",
                        "title": "Heat Stress",
                        "chunk_index": 0,
                    },
                )
            ]
        ),
    )
    monkeypatch.setattr(
        service.radar_service,
        "nearby",
        AsyncMock(
            return_value=DiseaseRadarNearbyResponse(
                hotspots=[],
                queried_at=datetime.now(timezone.utc),
                radius_km=25.0,
            )
        ),
    )

    result = await service.compile_context(USER_ID, FARM_ID, "heat stress on wheat", "en")

    assert len(result.citations) == 1
    assert result.citations[0].document_id == "icar-wheat-heat-stress-rajasthan"
    assert "icar-wheat-heat-stress-rajasthan:0" in result.rag_chunk_ids


def test_infer_topic_from_query() -> None:
    assert ContextCompilerService._infer_topic_from_query("heat stress on my crop") == "HEAT_STRESS"
    assert ContextCompilerService._infer_topic_from_query("npk fertilizer schedule") == "FERTILIZER"
