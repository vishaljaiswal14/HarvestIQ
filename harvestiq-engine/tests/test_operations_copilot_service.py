from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from bson import ObjectId

from app.models.alert_severity_schemas import AlertSeverityResult, AlertSeveritySignals
from app.models.day8_schemas_actions import ActionCard, AdvisoryActionsResponse
from app.models.day6_schemas import CoreIntelligence, StressMomentumResult, YieldRiskResult
from app.models.engine_schemas import ExplanationPayload
from app.models.yield_protection_schemas import YieldProtectionBreakdown, YieldProtectionScoreResponse
from app.services.operations_copilot_service import OperationsCopilotService

FARM_ID = str(ObjectId())
USER_ID = str(ObjectId())


def _core(fsi=0.15) -> CoreIntelligence:
    return CoreIntelligence(
        farm_id=FARM_ID,
        crop_type="WHEAT",
        stage="Tillering",
        fsi=fsi,
        fsi_classification="LOW_STRESS",
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
            risk_band="LOW",
            estimated_risk_percent=5.0,
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


def _severity(tier="LOW") -> AlertSeverityResult:
    return AlertSeverityResult(
        farm_id=FARM_ID,
        severity_tier=tier,
        severity_rank=1,
        critical_triggers=[],
        generated_because=["FSI within safe range"],
        explanation=ExplanationPayload(summary="test", inputs={}, primary_factor="MOISTURE"),
        signals=AlertSeveritySignals(
            fsi=0.15,
            fsi_classification="LOW_STRESS",
            confirmed_disease=False,
            possible_or_confirmed_disease=False,
            active_high_alerts=0,
            active_medium_alerts=0,
            advisory_priority="LOW",
            recent_sos=False,
            weather_temp_c=28.0,
            rainfall_deficit=0.1,
            rainfall_deficit_alert_active=False,
        ),
        evaluated_at=datetime.now(timezone.utc),
    )


def _advisory(priority="LOW") -> AdvisoryActionsResponse:
    return AdvisoryActionsResponse(
        priority=priority,
        situation_summary="Farm conditions are optimal.",
        today_actions=[],
        this_week_actions=[
            ActionCard(
                card_type="GREEN",
                problem="Routine Checks",
                action="Continue monitoring",
                deadline="This week",
                expected_impact="Maintain healthy growth",
            )
        ],
        ignore_risk="No immediate risks.",
        why_generated=["FSI = 15% (safe bounds)"],
    )


def _score_response() -> YieldProtectionScoreResponse:
    return YieldProtectionScoreResponse(
        farm_id=FARM_ID,
        score=88.0,
        band="PROTECTED",
        breakdown=YieldProtectionBreakdown(
            disease_risk=25, stress_risk=22, alert_burden=25, advisory_compliance=16
        ),
        trend="STABLE",
        trend_delta=0,
        top_risk="No significant risks detected",
        risk_reduction_impact="Low immediate risk reduction needed.",
        potential_loss_prevention_band="LOW",
        explanation=ExplanationPayload(summary="ok", inputs={}, primary_factor="MOISTURE"),
        calculated_at=datetime.now(timezone.utc),
    )


@pytest.mark.asyncio
async def test_generate_plan_orchestrates_existing_engines(monkeypatch) -> None:
    db = MagicMock()
    db.farms.find_one = AsyncMock(return_value={"_id": ObjectId(FARM_ID)})
    db.copilot_plans.insert_one = AsyncMock(return_value=MagicMock(inserted_id=ObjectId()))
    db.copilot_action_completions.find = MagicMock(return_value=_empty_cursor())
    db.disease_reports.find_one = AsyncMock(return_value=None)

    service = OperationsCopilotService(db)
    field_context = MagicMock()
    field_context.weather.current.humidity = 50.0

    monkeypatch.setattr(
        "app.services.context_compiler_service.ContextCompilerService._build_core_intelligence",
        AsyncMock(return_value=_core()),
    )
    monkeypatch.setattr(
        "app.services.stress_index_service.StressIndexService.build_field_context",
        AsyncMock(return_value=field_context),
    )
    monkeypatch.setattr(
        service.advisory_service,
        "get_actions",
        AsyncMock(return_value=_advisory()),
    )
    monkeypatch.setattr(
        "app.services.alert_severity_service.AlertSeverityService.evaluate",
        AsyncMock(return_value=_severity("LOW")),
    )
    monkeypatch.setattr(
        service.score_service,
        "compute",
        AsyncMock(return_value=_score_response()),
    )
    monkeypatch.setattr(
        service.score_service,
        "_load_unread_alerts",
        AsyncMock(return_value=[]),
    )

    plan = await service.generate_plan(USER_ID, FARM_ID, persist=True)

    assert plan.priority == "LOW"
    assert plan.severity_tier == "LOW"
    assert plan.yield_protection_score == 88.0
    assert len(plan.preventive_actions) >= 1
    assert plan.today_actions == []
    for action in plan.preventive_actions + plan.this_week_actions:
        assert action.why
        assert action.if_ignored
        assert action.expected_benefit


@pytest.mark.asyncio
async def test_critical_severity_raises_priority(monkeypatch) -> None:
    db = MagicMock()
    db.farms.find_one = AsyncMock(return_value={"_id": ObjectId(FARM_ID)})
    db.copilot_plans.insert_one = AsyncMock(return_value=MagicMock(inserted_id=ObjectId()))
    db.copilot_action_completions.find = MagicMock(return_value=_empty_cursor())
    db.disease_reports.find_one = AsyncMock(return_value=None)

    service = OperationsCopilotService(db)
    field_context = MagicMock()
    field_context.weather.current.humidity = 50.0

    advisory = _advisory("HIGH")
    advisory.today_actions = [
        ActionCard(
            card_type="RED",
            problem="High field stress",
            action="Irrigate immediately",
            deadline="Within 24 hours",
            expected_impact="Stabilize crop",
        )
    ]

    monkeypatch.setattr(
        "app.services.context_compiler_service.ContextCompilerService._build_core_intelligence",
        AsyncMock(return_value=_core(0.78)),
    )
    monkeypatch.setattr(
        "app.services.stress_index_service.StressIndexService.build_field_context",
        AsyncMock(return_value=field_context),
    )
    monkeypatch.setattr(service.advisory_service, "get_actions", AsyncMock(return_value=advisory))
    monkeypatch.setattr(
        "app.services.alert_severity_service.AlertSeverityService.evaluate",
        AsyncMock(return_value=_severity("CRITICAL")),
    )
    monkeypatch.setattr(service.score_service, "compute", AsyncMock(return_value=_score_response()))
    monkeypatch.setattr(service.score_service, "_load_unread_alerts", AsyncMock(return_value=[]))

    plan = await service.generate_plan(USER_ID, FARM_ID, persist=True)
    assert plan.priority == "EMERGENCY"
    assert plan.severity_tier == "CRITICAL"
    assert len(plan.today_actions) == 1
    assert plan.today_actions[0].why


@pytest.mark.asyncio
async def test_complete_action_updates_score(monkeypatch) -> None:
    db = MagicMock()
    plan_id = str(ObjectId())
    db.copilot_plans.find_one = AsyncMock(
        return_value={
            "_id": ObjectId(plan_id),
            "actions": [{"id": "act1", "priority": "HIGH"}],
        }
    )

    service = OperationsCopilotService(db)
    monkeypatch.setattr(
        service.score_service,
        "record_action_completion",
        AsyncMock(return_value=_score_response()),
    )

    result = await service.complete_action(USER_ID, FARM_ID, "act1", plan_id)
    assert result.completed is True
    assert result.yield_protection_score == 88.0


def _empty_cursor():
    async def _gen():
        return
        yield  # pragma: no cover

    class C:
        def __aiter__(self):
            return _gen()

    return C()
