from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from bson import ObjectId

from app.core.constants.alerts import (
    RULE_FSI_HIGH,
    RULE_RAINFALL_DEFICIT,
    RULE_THERMAL_HIGH,
)
from app.models.engine_schemas import (
    CropCharacteristicsInDB,
    CropStageDefinition,
    DailyGddEntry,
    FsiComponents,
    StressIndexResponse,
    TriggerEvaluationRequest,
    WeatherCurrent,
    WeatherForecastDay,
    WeatherForecastResponse,
)
from app.services.alert_service import AlertService
from app.services.stress_index_service import FieldContext

FARM_ID = str(ObjectId())
USER_ID = str(ObjectId())
CYCLE_ID = ObjectId()


def _rules() -> list[dict]:
    return [
        {
            "rule_id": RULE_THERMAL_HIGH,
            "severity": "HIGH",
            "enabled": True,
            "threshold": 38.0,
            "primary_factor": "THERMAL",
            "title": "High temperature stress",
            "message_template": "Current temperature {current_temp}°C exceeds safe limit of {threshold}°C during {stage} stage.",
        },
        {
            "rule_id": RULE_RAINFALL_DEFICIT,
            "severity": "MEDIUM",
            "enabled": True,
            "threshold": 0.7,
            "primary_factor": "MOISTURE",
            "title": "Rainfall deficit detected",
            "message_template": "Rainfall deficit index {rainfall_deficit} indicates moisture stress during {stage} stage.",
        },
        {
            "rule_id": RULE_FSI_HIGH,
            "severity": "HIGH",
            "enabled": True,
            "threshold": 0.67,
            "primary_factor": "THERMAL",
            "title": "High field stress index",
            "message_template": "Field stress index {fsi} is HIGH during {stage} stage.",
        },
    ]


def _stress_result() -> StressIndexResponse:
    now = datetime.now(timezone.utc)
    return StressIndexResponse(
        farm_id=FARM_ID,
        crop_cycle_id=str(CYCLE_ID),
        crop_type="WHEAT",
        stage="Tillering",
        fsi=0.75,
        classification="HIGH_STRESS",
        primary_factor="THERMAL",
        components=FsiComponents(temp_stress=0.9, rainfall_deficit=1.0, gdd_scale=0.3),
        calculated_at=now,
        explanation={
            "summary": "FSI is 0.75 (High Stress) primarily due to thermal stress.",
            "inputs": {"current_temp": 41.0},
            "primary_factor": "THERMAL",
        },
    )


def _field_context() -> FieldContext:
    from datetime import date

    forecast = [
        WeatherForecastDay(
            date=date(2026, 6, 1),
            temp_min=35.0,
            temp_max=41.0,
            humidity=30.0,
            precipitation=0.0,
            wind_speed=10.0,
        )
    ]
    weather = WeatherForecastResponse(
        farm_id=FARM_ID,
        current=WeatherCurrent(temp=41.0, humidity=30.0, wind_speed=10.0, precipitation=0.0),
        forecast=forecast,
        daily_gdd=[DailyGddEntry(date=date(2026, 6, 1), gdd=15.0)],
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


@pytest.mark.asyncio
async def test_thermal_rule_triggers_alert() -> None:
    db = MagicMock()

    async def fake_find(_query):
        for rule in _rules():
            yield rule

    db.system_rules.find = MagicMock(return_value=fake_find({}))
    db.alerts.find_one = AsyncMock(return_value=None)
    db.alerts.insert_one = AsyncMock(return_value=MagicMock(inserted_id=ObjectId()))

    service = AlertService(db)
    created = await service._evaluate_and_persist(
        USER_ID,
        FARM_ID,
        _field_context(),
        _stress_result(),
    )

    rule_ids = {alert.rule_id for alert in created}
    assert RULE_THERMAL_HIGH in rule_ids
    assert RULE_FSI_HIGH in rule_ids
    assert db.alerts.insert_one.call_count >= 2


@pytest.mark.asyncio
async def test_duplicate_alert_is_skipped() -> None:
    db = MagicMock()

    async def fake_find(_query):
        for rule in [_rules()[0]]:
            yield rule

    db.system_rules.find = MagicMock(return_value=fake_find({}))
    db.alerts.find_one = AsyncMock(return_value={"_id": ObjectId()})
    db.alerts.insert_one = AsyncMock()

    service = AlertService(db)
    created = await service._evaluate_and_persist(
        USER_ID,
        FARM_ID,
        _field_context(),
        _stress_result(),
    )

    assert created == []
    db.alerts.insert_one.assert_not_called()


@pytest.mark.asyncio
async def test_trigger_evaluation_uses_single_weather_fetch(monkeypatch) -> None:
    db = MagicMock()
    service = AlertService(db)
    context = _field_context()

    service.stress_service.build_field_context = AsyncMock(return_value=context)
    service.stress_service.calculate_fsi_from_context = MagicMock(return_value=_stress_result())
    service._evaluate_and_persist = AsyncMock(return_value=[])

    severity_mock = AsyncMock(
        return_value=MagicMock(
            severity_tier="LOW",
            model_dump=lambda **kwargs: {"severity_tier": "LOW"},
        )
    )
    monkeypatch.setattr(
        "app.services.alert_severity_service.AlertSeverityService.evaluate",
        severity_mock,
    )
    escalation_start = AsyncMock(return_value="esc_id")
    monkeypatch.setattr(
        "app.services.alert_escalation_service.AlertEscalationService.start_for_alert",
        escalation_start,
    )

    result = await service.trigger_evaluation(
        USER_ID,
        TriggerEvaluationRequest(farm_id=FARM_ID),
    )

    service.stress_service.build_field_context.assert_called_once()
    assert result.evaluated_rules == 3


def test_rule_passes_thermal() -> None:
    service = AlertService(MagicMock())
    rule = _rules()[0]
    assert service._rule_passes(rule, {"current_temp": 41.0, "rainfall_deficit": 0.0, "fsi": 0.5})


def test_rule_passes_rainfall_deficit() -> None:
    service = AlertService(MagicMock())
    rule = _rules()[1]
    assert service._rule_passes(rule, {"current_temp": 30.0, "rainfall_deficit": 0.8, "fsi": 0.5})
