from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from bson import ObjectId

from app.core.constants.alert_severity import (
    SEVERITY_CRITICAL,
    SEVERITY_HIGH,
    SEVERITY_LOW,
    SEVERITY_MEDIUM,
    TRIGGER_ADVISORY_EMERGENCY,
    TRIGGER_CONFIRMED_DISEASE_HIGH_FSI,
    TRIGGER_MULTIPLE_HIGH_ALERTS,
    TRIGGER_RECENT_SOS,
)
from app.core.constants.disease import DISEASE_STATUS_CONFIRMED
from app.models.alert_severity_schemas import AlertSeveritySignals
from app.models.day8_schemas_actions import AdvisoryActionsResponse
from app.models.engine_schemas import (
    CropCharacteristicsInDB,
    CropStageDefinition,
    DailyGddEntry,
    FsiComponents,
    StressIndexResponse,
    WeatherCurrent,
    WeatherForecastDay,
    WeatherForecastResponse,
)
from app.services.alert_severity_service import AlertSeverityService
from app.services.stress_index_service import FieldContext

FARM_ID = str(ObjectId())
USER_ID = str(ObjectId())
CYCLE_ID = ObjectId()


def _stress_result(fsi: float = 0.5) -> StressIndexResponse:
    now = datetime.now(timezone.utc)
    classification = "LOW_STRESS"
    if fsi >= 0.67:
        classification = "HIGH_STRESS"
    elif fsi >= 0.35:
        classification = "MEDIUM_STRESS"
    return StressIndexResponse(
        farm_id=FARM_ID,
        crop_cycle_id=str(CYCLE_ID),
        crop_type="WHEAT",
        stage="Tillering",
        fsi=fsi,
        classification=classification,
        primary_factor="MOISTURE",
        components=FsiComponents(temp_stress=0.3, rainfall_deficit=0.2, gdd_scale=0.2),
        calculated_at=now,
        explanation={"summary": "test", "inputs": {}, "primary_factor": "MOISTURE"},
    )


def _field_context() -> FieldContext:
    from datetime import date

    forecast = [
        WeatherForecastDay(
            date=date(2026, 6, 1),
            temp_min=30.0,
            temp_max=36.0,
            humidity=40.0,
            precipitation=0.0,
            wind_speed=8.0,
        )
    ]
    weather = WeatherForecastResponse(
        farm_id=FARM_ID,
        current=WeatherCurrent(temp=36.0, humidity=40.0, wind_speed=8.0, precipitation=0.0),
        forecast=forecast,
        daily_gdd=[DailyGddEntry(date=date(2026, 6, 1), gdd=12.0)],
        source="CACHE_HIT",
        cached_at=datetime.now(timezone.utc),
    )
    characteristics = CropCharacteristicsInDB(
        _id=ObjectId(),
        crop_type="WHEAT",
        display_name="Wheat",
        gdd_base_temp=10.0,
        stages=[CropStageDefinition(name="Tillering", gdd_min=100, gdd_max=400)],
        stage_vulnerability={"Tillering": 0.60},
    )
    return FieldContext(
        farm={"_id": ObjectId(FARM_ID)},
        cycle={"_id": CYCLE_ID, "crop_type": "WHEAT"},
        characteristics=characteristics,
        weather=weather,
        stage_name="Tillering",
        current_gdd=200.0,
        current_stage_def=CropStageDefinition(name="Tillering", gdd_min=100, gdd_max=400),
    )


def _service_with_mocks(
    monkeypatch: pytest.MonkeyPatch,
    *,
    fsi: float = 0.5,
    disease_doc: dict | None = None,
    alerts: list[dict] | None = None,
    recent_sos: bool = False,
    advisory_priority: str = "LOW",
) -> AlertSeverityService:
    db = MagicMock()
    db.farms = MagicMock()
    db.farms.find_one = AsyncMock(
        return_value={"_id": ObjectId(FARM_ID), "user_id": ObjectId(USER_ID)}
    )
    db.disease_reports.find_one = AsyncMock(return_value=disease_doc)
    db.sos_actions.find_one = AsyncMock(return_value={"_id": ObjectId()} if recent_sos else None)
    db.alert_severity_logs.insert_one = AsyncMock(
        return_value=MagicMock(inserted_id=ObjectId())
    )

    async def fake_alerts_cursor(*_args, **_kwargs):
        for alert in alerts or []:
            yield alert

    mock_cursor = MagicMock()
    mock_cursor.__aiter__ = lambda self: fake_alerts_cursor()
    db.alerts.find = MagicMock(return_value=mock_cursor)

    service = AlertSeverityService(db)
    monkeypatch.setattr(
        service.stress_service,
        "build_field_context",
        AsyncMock(return_value=_field_context()),
    )
    monkeypatch.setattr(
        service.stress_service,
        "calculate_fsi_from_context",
        MagicMock(return_value=_stress_result(fsi)),
    )
    monkeypatch.setattr(
        service.advisory_service,
        "get_actions",
        AsyncMock(
            return_value=AdvisoryActionsResponse(
                priority=advisory_priority,
                situation_summary="",
                today_actions=[],
                this_week_actions=[],
                ignore_risk="",
                why_generated=[],
            )
        ),
    )
    return service


@pytest.mark.asyncio
async def test_severity_low_when_no_signals(monkeypatch: pytest.MonkeyPatch) -> None:
    service = _service_with_mocks(monkeypatch, fsi=0.2)
    result = await service.evaluate(USER_ID, FARM_ID, persist=False)
    assert result.severity_tier == SEVERITY_LOW
    assert result.critical_triggers == []


@pytest.mark.asyncio
async def test_severity_medium_from_fsi_band(monkeypatch: pytest.MonkeyPatch) -> None:
    service = _service_with_mocks(monkeypatch, fsi=0.45)
    result = await service.evaluate(USER_ID, FARM_ID, persist=False)
    assert result.severity_tier == SEVERITY_MEDIUM


@pytest.mark.asyncio
async def test_severity_high_from_fsi(monkeypatch: pytest.MonkeyPatch) -> None:
    service = _service_with_mocks(monkeypatch, fsi=0.72)
    result = await service.evaluate(USER_ID, FARM_ID, persist=False)
    assert result.severity_tier == SEVERITY_HIGH


@pytest.mark.asyncio
async def test_critical_confirmed_disease_high_fsi(monkeypatch: pytest.MonkeyPatch) -> None:
    service = _service_with_mocks(
        monkeypatch,
        fsi=0.82,
        disease_doc={
            "deterministic_status": DISEASE_STATUS_CONFIRMED,
            "disease_name": "Wheat Rust",
            "disease": "WHEAT_RUST",
        },
    )
    result = await service.evaluate(USER_ID, FARM_ID, persist=False)
    assert result.severity_tier == SEVERITY_CRITICAL
    assert TRIGGER_CONFIRMED_DISEASE_HIGH_FSI in result.critical_triggers
    assert any("Wheat Rust" in item for item in result.generated_because)


@pytest.mark.asyncio
async def test_critical_multiple_high_alerts(monkeypatch: pytest.MonkeyPatch) -> None:
    alerts = [
        {"rule_id": "RULE_FSI_HIGH", "severity": "HIGH", "read": False},
        {"rule_id": "RULE_THERMAL_HIGH", "severity": "HIGH", "read": False},
    ]
    service = _service_with_mocks(monkeypatch, fsi=0.4, alerts=alerts)
    result = await service.evaluate(USER_ID, FARM_ID, persist=False)
    assert result.severity_tier == SEVERITY_CRITICAL
    assert TRIGGER_MULTIPLE_HIGH_ALERTS in result.critical_triggers


@pytest.mark.asyncio
async def test_critical_recent_sos(monkeypatch: pytest.MonkeyPatch) -> None:
    service = _service_with_mocks(monkeypatch, fsi=0.2, recent_sos=True)
    result = await service.evaluate(USER_ID, FARM_ID, persist=False)
    assert result.severity_tier == SEVERITY_CRITICAL
    assert TRIGGER_RECENT_SOS in result.critical_triggers


@pytest.mark.asyncio
async def test_critical_advisory_emergency(monkeypatch: pytest.MonkeyPatch) -> None:
    service = _service_with_mocks(monkeypatch, fsi=0.2, advisory_priority="EMERGENCY")
    result = await service.evaluate(USER_ID, FARM_ID, persist=False)
    assert result.severity_tier == SEVERITY_CRITICAL
    assert TRIGGER_ADVISORY_EMERGENCY in result.critical_triggers


@pytest.mark.asyncio
async def test_explainability_includes_fsi_and_rainfall(monkeypatch: pytest.MonkeyPatch) -> None:
    alerts = [{"rule_id": "RULE_RAINFALL_DEFICIT", "severity": "MEDIUM", "read": False}]
    service = _service_with_mocks(monkeypatch, fsi=0.55, alerts=alerts)
    result = await service.evaluate(USER_ID, FARM_ID, persist=False)
    joined = " ".join(result.generated_because)
    assert "FSI =" in joined
    assert "Rainfall Deficit active" in joined


@pytest.mark.asyncio
async def test_persist_severity_log(monkeypatch: pytest.MonkeyPatch) -> None:
    service = _service_with_mocks(monkeypatch, fsi=0.72)
    result = await service.evaluate(USER_ID, FARM_ID, persist=True)
    assert result.log_id is not None
    service.db.alert_severity_logs.insert_one.assert_awaited_once()


def test_classify_base_tier_only() -> None:
    service = AlertSeverityService(MagicMock())
    tier, triggers, _because = service._classify(
        AlertSeveritySignals(
            fsi=0.72,
            fsi_classification="HIGH_STRESS",
            confirmed_disease=False,
            active_high_alerts=1,
            active_medium_alerts=0,
            active_alert_rules=["RULE_FSI_HIGH"],
        )
    )
    assert tier == SEVERITY_HIGH
    assert triggers == []
