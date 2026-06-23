from unittest.mock import AsyncMock, MagicMock

import pytest
from bson import ObjectId
from fastapi import HTTPException

from app.models.day5_schemas import AdvisoryAskRequest, CompiledContextResult
from app.models.day6_schemas import CoreIntelligence, StressMomentumResult, YieldRiskResult
from app.services.advisory_service import AdvisoryService
from unittest.mock import patch

@pytest.fixture(autouse=True)
def mock_synthesize_advisory():
    with patch("app.integrations.gemini_client.OpenRouterClient.synthesize_advisory", side_effect=Exception("Mock API failure")):
        yield

FARM_ID = str(ObjectId())
USER_ID = str(ObjectId())


def _compiled() -> CompiledContextResult:
    return CompiledContextResult(
        context_package="# context",
        context_hash="abc123",
        citations=[],
        explainability={
            "summary": "Deterministic resolution",
            "inputs": {"fsi": 0.82},
            "primary_factor": "THERMAL",
        },
        rag_chunk_ids=[],
        intelligence_snapshot_version="v3",
        mitigation_locked=True,
        language="hi",
    )


def _mock_core() -> CoreIntelligence:
    return CoreIntelligence(
        farm_id=FARM_ID,
        crop_type="WHEAT",
        stage="Tillering",
        fsi=0.75,
        fsi_classification="HIGH_STRESS",
        primary_factor="MOISTURE",
        current_gdd=150.0,
        soil_health_index=85.0,
        stress_momentum=StressMomentumResult(
            direction="STABLE",
            momentum_score=0.0,
            fsi_delta=0.0,
            insufficient_history=True,
            window_days=7,
        ),
        yield_risk=YieldRiskResult(
            risk_band="MEDIUM",
            estimated_risk_percent=45.0,
            contributing_factors=["FSI"],
        ),
        mitigation_locked=False,
        disease_present=False,
        radar_high_nearby=False,
        nearby_outbreaks=[],
        alert_rules=[],
        stage_vulnerability=0.5,
        cycle_status="ACTIVE",
    )


@pytest.mark.asyncio
async def test_ask_persists_deterministic_advisory_log(monkeypatch) -> None:
    db = MagicMock()
    db.advisory_logs.insert_one = AsyncMock(return_value=MagicMock(inserted_id=ObjectId()))

    service = AdvisoryService(db)
    
    # Mock context compiler and helper services
    monkeypatch.setattr(service.context_compiler, "compile_context", AsyncMock(return_value=_compiled()))
    
    field_context = MagicMock()
    field_context.weather.current.wind_speed = 12.0
    field_context.weather.current.temp = 28.0
    field_context.weather.current.humidity = 70.0
    field_context.weather.current.precipitation = 0.0
    field_context.weather.forecast = [MagicMock(precipitation=0.0) for _ in range(3)]
    
    monkeypatch.setattr(service.context_compiler.stress_service, "build_field_context", AsyncMock(return_value=field_context))
    monkeypatch.setattr(service.context_compiler, "_build_core_intelligence", AsyncMock(return_value=_mock_core()))
    monkeypatch.setattr(service.context_compiler, "_count_unread_alerts", AsyncMock(return_value=1))
    
    # Mock window evaluation response
    opt_resp = MagicMock()
    opt_resp.safe = True
    opt_resp.reasons = []
    monkeypatch.setattr(service.optimizer, "evaluate", AsyncMock(return_value=opt_resp))

    result = await service.ask(
        USER_ID,
        AdvisoryAskRequest(farm_id=FARM_ID, query="should I irrigate?"),
        "en",
    )

    assert "Irrigation Advisory" in result.synthesis
    assert "FSI" in result.synthesis
    assert result.intelligence_snapshot_version == "v3"
    assert len(result.citations) == 0
    assert result.explainability.inputs["confidence_level"] == "HIGH"
    db.advisory_logs.insert_one.assert_called_once()
    
    saved = db.advisory_logs.insert_one.call_args[0][0]
    assert saved["intelligence_snapshot_version"] == "v3"
    assert saved["context_hash"] == "abc123"


@pytest.mark.asyncio
async def test_compound_intents_combines_advice(monkeypatch) -> None:
    db = MagicMock()
    db.advisory_logs.insert_one = AsyncMock(return_value=MagicMock(inserted_id=ObjectId()))
    
    service = AdvisoryService(db)
    monkeypatch.setattr(service.context_compiler, "compile_context", AsyncMock(return_value=_compiled()))
    
    field_context = MagicMock()
    field_context.weather.current.wind_speed = 10.0
    field_context.weather.current.temp = 32.0
    field_context.weather.current.humidity = 55.0
    field_context.weather.current.precipitation = 0.0
    field_context.weather.forecast = [MagicMock(precipitation=0.0) for _ in range(3)]
    
    monkeypatch.setattr(service.context_compiler.stress_service, "build_field_context", AsyncMock(return_value=field_context))
    monkeypatch.setattr(service.context_compiler, "_build_core_intelligence", AsyncMock(return_value=_mock_core()))
    monkeypatch.setattr(service.context_compiler, "_count_unread_alerts", AsyncMock(return_value=0))
    monkeypatch.setattr(service.context_compiler, "_build_soil_section", AsyncMock(return_value=("- soil", None)))
    
    opt_resp = MagicMock()
    opt_resp.safe = True
    opt_resp.reasons = []
    monkeypatch.setattr(service.optimizer, "evaluate", AsyncMock(return_value=opt_resp))
    
    # Compound query triggering IRRIGATION & SPRAY & FERTILIZER
    result = await service.ask(
        USER_ID,
        AdvisoryAskRequest(farm_id=FARM_ID, query="Should I irrigate and spray fertilizer?"),
        "en",
    )
    
    assert "Irrigation Advisory" in result.synthesis
    assert "Fertilizer Advisory" in result.synthesis
    assert "Spray Advisory" in result.synthesis
    assert "confidence_level" in result.explainability.inputs
    assert result.explainability.inputs["confidence_level"] == "HIGH"


@pytest.mark.asyncio
async def test_low_confidence_when_soil_data_missing(monkeypatch) -> None:
    db = MagicMock()
    db.advisory_logs.insert_one = MagicMock()
    db.advisory_logs.insert_one = AsyncMock(return_value=MagicMock(inserted_id=ObjectId()))
    
    service = AdvisoryService(db)
    monkeypatch.setattr(service.context_compiler, "compile_context", AsyncMock(return_value=_compiled()))
    
    field_context = MagicMock()
    field_context.weather.current.wind_speed = 5.0
    field_context.weather.current.temp = 30.0
    field_context.weather.current.humidity = 60.0
    field_context.weather.current.precipitation = 0.0
    field_context.weather.forecast = [MagicMock(precipitation=0.0) for _ in range(3)]
    
    monkeypatch.setattr(service.context_compiler.stress_service, "build_field_context", AsyncMock(return_value=field_context))
    monkeypatch.setattr(service.context_compiler, "compile_health_snapshot", AsyncMock(return_value=MagicMock(health_band="FAIR", health_score=80.0)))
    
    # Missing soil record (soil_health_index = None)
    core_missing_soil = _mock_core()
    core_missing_soil.soil_health_index = None
    monkeypatch.setattr(service.context_compiler, "_build_core_intelligence", AsyncMock(return_value=core_missing_soil))
    monkeypatch.setattr(service.context_compiler, "_count_unread_alerts", AsyncMock(return_value=0))
    
    opt_resp = MagicMock()
    opt_resp.safe = True
    monkeypatch.setattr(service.optimizer, "evaluate", AsyncMock(return_value=opt_resp))
    
    result = await service.ask(
        USER_ID,
        AdvisoryAskRequest(farm_id=FARM_ID, query="overall status"),
        "en",
    )
    
    # Missing soil records should drop confidence to LOW
    assert result.explainability.inputs["confidence_level"] == "LOW"


@pytest.mark.asyncio
async def test_empty_query_returns_422() -> None:
    service = AdvisoryService(MagicMock())
    with pytest.raises(HTTPException) as exc:
        await service.ask(USER_ID, AdvisoryAskRequest(farm_id=FARM_ID, query="   "), "en")
    assert exc.value.status_code == 422
