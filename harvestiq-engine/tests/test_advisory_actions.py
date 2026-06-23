from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from bson import ObjectId

from app.models.day8_schemas_actions import AdvisoryActionsResponse
from app.models.day6_schemas import CoreIntelligence, StressMomentumResult, YieldRiskResult
from app.services.advisory_service import AdvisoryService

FARM_ID = str(ObjectId())
USER_ID = str(ObjectId())

def _mock_core(fsi=0.12, classification="LOW_STRESS", primary_factor="MOISTURE", disease_present=False) -> CoreIntelligence:
    return CoreIntelligence(
        farm_id=FARM_ID,
        crop_type="WHEAT",
        stage="Tillering",
        fsi=fsi,
        fsi_classification=classification,
        primary_factor=primary_factor,
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
            risk_band="LOW" if fsi < 0.35 else "MEDIUM" if fsi < 0.65 else "HIGH",
            estimated_risk_percent=0.0 if fsi < 0.35 else 15.0 if fsi < 0.65 else 45.0,
            contributing_factors=["FSI"],
        ),
        mitigation_locked=False,
        disease_present=disease_present,
        radar_high_nearby=False,
        nearby_outbreaks=[],
        alert_rules=[],
        stage_vulnerability=0.5,
        cycle_status="ACTIVE",
    )

@pytest.mark.asyncio
async def test_actions_healthy_farm(monkeypatch) -> None:
    db = MagicMock()
    db.disease_reports.find_one = AsyncMock(return_value=None)
    
    mock_cursor = AsyncMock()
    mock_cursor.__aiter__.return_value = []
    db.alerts.find = MagicMock(return_value=mock_cursor)

    service = AdvisoryService(db)
    
    field_context = MagicMock()
    field_context.weather.current.wind_speed = 10.0
    field_context.weather.current.temp = 25.0
    field_context.weather.current.humidity = 50.0
    field_context.weather.forecast = []
    
    monkeypatch.setattr(service.context_compiler.stress_service, "build_field_context", AsyncMock(return_value=field_context))
    monkeypatch.setattr(service.context_compiler, "_build_core_intelligence", AsyncMock(return_value=_mock_core(fsi=0.12)))

    res = await service.get_actions(USER_ID, FARM_ID, "en")
    
    assert res.priority == "LOW"
    assert "optimal" in res.situation_summary
    assert len(res.today_actions) == 0
    assert len(res.this_week_actions) == 1
    assert res.this_week_actions[0].card_type == "GREEN"
    assert "Routine Checks" in res.this_week_actions[0].problem
    assert "No immediate yield risks" in res.ignore_risk
    assert "safe bounds" in res.why_generated[0]

@pytest.mark.asyncio
async def test_actions_disease_outbreak(monkeypatch) -> None:
    db = MagicMock()
    latest_disease = {
        "farm_id": ObjectId(FARM_ID),
        "disease": "WHEAT_RUST",
        "disease_name": "Wheat Rust",
        "deterministic_status": "CONFIRMED_DISEASE",
        "created_at": datetime.now(timezone.utc)
    }
    db.disease_reports.find_one = AsyncMock(return_value=latest_disease)
    
    mock_cursor = AsyncMock()
    mock_cursor.__aiter__.return_value = []
    db.alerts.find = MagicMock(return_value=mock_cursor)

    service = AdvisoryService(db)
    
    field_context = MagicMock()
    field_context.weather.current.humidity = 60.0
    field_context.weather.current.temp = 25.0
    
    monkeypatch.setattr(service.context_compiler.stress_service, "build_field_context", AsyncMock(return_value=field_context))
    monkeypatch.setattr(service.context_compiler, "_build_core_intelligence", AsyncMock(return_value=_mock_core(fsi=0.15, disease_present=True)))

    res = await service.get_actions(USER_ID, FARM_ID, "en")
    
    assert res.priority == "HIGH"
    assert "showing signs of Wheat Rust" in res.situation_summary
    assert len(res.today_actions) == 1
    assert res.today_actions[0].card_type == "RED"
    assert "Wheat Rust infection detected" in res.today_actions[0].problem
    assert "Propiconazole" in res.today_actions[0].action
    assert "10-20%" in res.ignore_risk
    assert "Wheat Rust detected" in res.why_generated

@pytest.mark.asyncio
async def test_actions_high_fsi(monkeypatch) -> None:
    db = MagicMock()
    db.disease_reports.find_one = AsyncMock(return_value=None)
    
    mock_cursor = AsyncMock()
    mock_cursor.__aiter__.return_value = []
    db.alerts.find = MagicMock(return_value=mock_cursor)

    service = AdvisoryService(db)
    
    field_context = MagicMock()
    field_context.weather.current.humidity = 60.0
    field_context.weather.current.temp = 32.0
    
    monkeypatch.setattr(service.context_compiler.stress_service, "build_field_context", AsyncMock(return_value=field_context))
    monkeypatch.setattr(service.context_compiler, "_build_core_intelligence", AsyncMock(return_value=_mock_core(fsi=0.72, primary_factor="MOISTURE")))

    res = await service.get_actions(USER_ID, FARM_ID, "en")
    
    assert res.priority == "HIGH"
    assert "high stress due to MOISTURE" in res.situation_summary
    assert len(res.today_actions) == 1
    assert res.today_actions[0].card_type == "RED"
    assert "FSI: 72%" in res.today_actions[0].problem
    assert "Irrigate your farm immediately" in res.today_actions[0].action
    assert "5-10%" in res.ignore_risk
    assert "FSI = 72%" in res.why_generated

@pytest.mark.asyncio
async def test_actions_multiple_alerts_and_humidity(monkeypatch) -> None:
    db = MagicMock()
    db.disease_reports.find_one = AsyncMock(return_value=None)
    
    mock_alerts = [
        {"rule_id": "RULE_RAINFALL_DEFICIT", "severity": "MEDIUM", "title": "Rainfall Deficit"},
        {"rule_id": "RULE_THERMAL_HIGH", "severity": "MEDIUM", "title": "High Thermal Stress"}
    ]
    
    async def mock_iter(*args, **kwargs):
        for a in mock_alerts:
            yield a
            
    mock_cursor = MagicMock()
    mock_cursor.__aiter__ = mock_iter
    db.alerts.find = MagicMock(return_value=mock_cursor)

    service = AdvisoryService(db)
    
    field_context = MagicMock()
    field_context.weather.current.humidity = 85.0
    field_context.weather.current.temp = 29.0
    
    monkeypatch.setattr(service.context_compiler.stress_service, "build_field_context", AsyncMock(return_value=field_context))
    monkeypatch.setattr(service.context_compiler, "_build_core_intelligence", AsyncMock(return_value=_mock_core(fsi=0.25)))

    res = await service.get_actions(USER_ID, FARM_ID, "en")
    
    assert res.priority == "MEDIUM"
    assert len(res.today_actions) == 0
    assert len(res.this_week_actions) == 3
    assert res.this_week_actions[0].card_type == "YELLOW"
    assert res.this_week_actions[1].card_type == "YELLOW"
    assert res.this_week_actions[2].card_type == "YELLOW"
    assert "Rainfall deficit alert active" in res.why_generated
    assert "High thermal stress alert active" in res.why_generated
    assert "Humidity above threshold (85%)" in res.why_generated

@pytest.mark.asyncio
async def test_actions_hindi_translation(monkeypatch) -> None:
    db = MagicMock()
    latest_disease = {
        "farm_id": ObjectId(FARM_ID),
        "disease": "WHEAT_RUST",
        "disease_name": "पीला रतुआ",
        "deterministic_status": "CONFIRMED_DISEASE",
        "created_at": datetime.now(timezone.utc)
    }
    db.disease_reports.find_one = AsyncMock(return_value=latest_disease)
    
    mock_cursor = AsyncMock()
    mock_cursor.__aiter__.return_value = []
    db.alerts.find = MagicMock(return_value=mock_cursor)

    service = AdvisoryService(db)
    
    field_context = MagicMock()
    field_context.weather.current.humidity = 60.0
    field_context.weather.current.temp = 25.0
    
    monkeypatch.setattr(service.context_compiler.stress_service, "build_field_context", AsyncMock(return_value=field_context))
    monkeypatch.setattr(service.context_compiler, "_build_core_intelligence", AsyncMock(return_value=_mock_core(fsi=0.15, disease_present=True)))

    res = await service.get_actions(USER_ID, FARM_ID, "hi")
    
    assert res.priority == "HIGH"
    assert "लक्षण दिखाई दे रहे हैं" in res.situation_summary
    assert len(res.today_actions) == 1
    assert res.today_actions[0].card_type == "RED"
    assert "संक्रमण का पता चला है" in res.today_actions[0].problem
    assert "कवकनाशी" in res.today_actions[0].action
    assert "10-20%" in res.ignore_risk
    assert "पीला रतुआ का पता चला" in res.why_generated
