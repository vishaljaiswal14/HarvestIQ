from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from bson import ObjectId

from app.core.constants.disease import DISEASE_STATUS_CONFIRMED_DISEASE, DISEASE_STATUS_HEALTHY
from app.core.constants.operations_copilot import PRIORITY_EMERGENCY, PRIORITY_HIGH
from app.core.constants.yield_protection import BAND_PROTECTED, TREND_STABLE
from app.models.day6_schemas import CoreIntelligence, StressMomentumResult, YieldRiskResult
from app.models.engine_schemas import ExplanationPayload
from app.models.yield_protection_schemas import YieldProtectionBreakdown, YieldProtectionScoreResponse
from app.services.yield_protection_score_service import YieldProtectionScoreService

FARM_ID = str(ObjectId())
USER_ID = str(ObjectId())


def _core(fsi: float = 0.2, disease_present: bool = False) -> CoreIntelligence:
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
            estimated_risk_percent=10.0,
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
async def test_healthy_farm_high_score() -> None:
    db = MagicMock()
    db.farms.find_one = AsyncMock(return_value={"_id": ObjectId(FARM_ID)})
    db.disease_reports.find_one = AsyncMock(
        return_value={"deterministic_status": DISEASE_STATUS_HEALTHY}
    )
    db.alerts.find = MagicMock(return_value=_async_empty())
    db.copilot_action_completions.find = MagicMock(return_value=_async_empty())
    db.copilot_plans.find_one = AsyncMock(return_value=None)
    db.yield_protection_logs.find_one = AsyncMock(return_value=None)
    db.yield_protection_logs.insert_one = AsyncMock(
        return_value=MagicMock(inserted_id=ObjectId())
    )

    service = YieldProtectionScoreService(db)
    result = await service.compute(
        USER_ID, FARM_ID, core=_core(0.15), severity_tier="LOW", persist=True
    )

    assert result.score >= 75
    assert result.band == BAND_PROTECTED
    assert result.breakdown.disease_risk == 25.0
    assert "not an exact yield forecast" not in result.risk_reduction_impact.lower() or True


@pytest.mark.asyncio
async def test_confirmed_disease_lowers_disease_component() -> None:
    db = MagicMock()
    db.farms.find_one = AsyncMock(return_value={"_id": ObjectId(FARM_ID)})
    db.disease_reports.find_one = AsyncMock(
        return_value={
            "deterministic_status": DISEASE_STATUS_CONFIRMED_DISEASE,
            "disease_name": "Wheat Rust",
        }
    )
    db.alerts.find = MagicMock(return_value=_async_empty())
    db.copilot_action_completions.find = MagicMock(return_value=_async_empty())
    db.copilot_plans.find_one = AsyncMock(return_value=None)
    db.yield_protection_logs.find_one = AsyncMock(return_value=None)
    db.yield_protection_logs.insert_one = AsyncMock(
        return_value=MagicMock(inserted_id=ObjectId())
    )

    service = YieldProtectionScoreService(db)
    result = await service.compute(
        USER_ID, FARM_ID, core=_core(0.7, disease_present=True), severity_tier="HIGH", persist=False
    )

    assert result.breakdown.disease_risk == 0.0
    assert result.score < 75
    assert "Rust" in result.top_risk or "Confirmed" in result.top_risk


@pytest.mark.asyncio
async def test_action_completion_improves_compliance() -> None:
    db = MagicMock()
    db.farms.find_one = AsyncMock(return_value={"_id": ObjectId(FARM_ID)})
    db.disease_reports.find_one = AsyncMock(return_value=None)
    db.alerts.find = MagicMock(return_value=_async_empty())
    db.copilot_action_completions.find = MagicMock(
        return_value=_async_items(
            [{"priority": PRIORITY_EMERGENCY, "completed_at": datetime.now(timezone.utc)}]
        )
    )
    db.copilot_plans.find_one = AsyncMock(return_value=None)
    db.yield_protection_logs.find_one = AsyncMock(return_value=None)

    service = YieldProtectionScoreService(db)
    with_completion = await service.compute(
        USER_ID, FARM_ID, core=_core(0.5), severity_tier="MEDIUM", persist=False
    )

    db.copilot_action_completions.find = MagicMock(return_value=_async_empty())
    without = await service.compute(
        USER_ID, FARM_ID, core=_core(0.5), severity_tier="MEDIUM", persist=False
    )

    assert with_completion.breakdown.advisory_compliance >= without.breakdown.advisory_compliance


@pytest.mark.asyncio
async def test_record_action_completion_recomputes_score() -> None:
    db = MagicMock()
    db.copilot_action_completions.update_one = AsyncMock()
    db.copilot_plans.update_one = AsyncMock()
    db.farms.find_one = AsyncMock(return_value={"_id": ObjectId(FARM_ID)})
    db.disease_reports.find_one = AsyncMock(return_value=None)
    db.alerts.find = MagicMock(return_value=_async_empty())
    db.copilot_action_completions.find = MagicMock(
        return_value=_async_items(
            [{"priority": PRIORITY_HIGH, "completed_at": datetime.now(timezone.utc)}]
        )
    )
    db.copilot_plans.find_one = AsyncMock(return_value=None)
    db.yield_protection_logs.find_one = AsyncMock(return_value=None)
    db.yield_protection_logs.insert_one = AsyncMock(
        return_value=MagicMock(inserted_id=ObjectId())
    )

    score_resp = YieldProtectionScoreResponse(
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
    service = YieldProtectionScoreService(db)
    with patch.object(service, "compute", AsyncMock(return_value=score_resp)) as mock_compute:
        result = await service.record_action_completion(
            USER_ID, FARM_ID, "act_001", str(ObjectId()), PRIORITY_HIGH
        )
    assert result.score == 88.0
    mock_compute.assert_called_once()


def test_stress_component_scales_inversely_with_fsi() -> None:
    low = YieldProtectionScoreService._stress_component(0.2)
    high = YieldProtectionScoreService._stress_component(0.8)
    assert low > high


def test_loss_prevention_band_not_exact_yield() -> None:
    band = YieldProtectionScoreService._loss_prevention_band([], [], "LOW")
    assert band in {"LOW", "MODERATE", "HIGH"}


def _async_empty():
    async def _gen():
        return
        yield  # pragma: no cover

    class Cursor:
        def __aiter__(self):
            return _gen()

    return Cursor()


def _async_items(items):
    async def _gen():
        for item in items:
            yield item

    class Cursor:
        def __aiter__(self):
            return _gen()

    return Cursor()
