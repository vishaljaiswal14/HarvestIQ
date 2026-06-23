from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from bson import ObjectId
from fastapi.testclient import TestClient

from app.api.deps import get_current_user
from app.core.database import get_database
from app.main import create_app
from app.models.day6_schemas import (
    BriefingResponse,
    BriefingSections,
    HealthCardResponse,
    InputWindowResponse,
    MarketPricesResponse,
    SchemesEligibleResponse,
    SimulatorResponse,
    SimulatorSnapshot,
    StressMomentumResult,
    YieldRiskResult,
)
from app.models.engine_schemas import ExplanationPayload

USER_ID = str(ObjectId())
FARM_ID = str(ObjectId())


def _momentum() -> StressMomentumResult:
    return StressMomentumResult(
        direction="STABLE",
        momentum_score=0.1,
        fsi_delta=0.02,
        insufficient_history=False,
        window_days=7,
    )


def _yield_risk() -> YieldRiskResult:
    return YieldRiskResult(
        risk_band="MEDIUM",
        estimated_risk_percent=45.0,
        contributing_factors=["FSI"],
    )


@pytest.fixture
def client(monkeypatch) -> TestClient:
    monkeypatch.setattr("app.main.connect_to_mongo", AsyncMock())
    monkeypatch.setattr("app.main.ensure_indexes", AsyncMock())
    monkeypatch.setattr("app.main.close_mongo_connection", AsyncMock())

    app = create_app()

    async def fake_user():
        return {"_id": ObjectId(USER_ID), "preferred_lang": "hi", "role": "FARMER"}

    app.dependency_overrides[get_current_user] = fake_user
    app.dependency_overrides[get_database] = lambda: MagicMock()

    now = datetime.now(timezone.utc)
    explanation = ExplanationPayload(
        summary="Deterministic explanation",
        inputs={"fsi": 0.5},
        primary_factor="THERMAL",
    )

    monkeypatch.setattr(
        "app.api.v1.optimizer.InputWindowOptimizerService.evaluate",
        AsyncMock(
            return_value=InputWindowResponse(
                farm_id=FARM_ID,
                action_type="SPRAY",
                safe=False,
                reasons=["Wind too high"],
                triggered_rules=["RULE_HIGH_WIND"],
                explanation=explanation,
                evaluated_at=now,
            )
        ),
    )
    monkeypatch.setattr(
        "app.api.v1.briefing.BriefingService.get_daily_briefing",
        AsyncMock(
            return_value=BriefingResponse(
                briefing_id=str(ObjectId()),
                farm_id=FARM_ID,
                synthesis="Morning briefing",
                language="hi",
                sections=BriefingSections(
                    stress_momentum=_momentum(),
                    yield_risk=_yield_risk(),
                    input_windows={"SPRAY": False},
                    eligible_schemes_count=1,
                ),
                explainability=explanation,
                intelligence_snapshot_version="v3",
                generated_at=now,
                source="ON_DEMAND",
            )
        ),
    )
    monkeypatch.setattr(
        "app.api.v1.schemes.SchemeEligibilityService.get_eligible",
        AsyncMock(
            return_value=SchemesEligibleResponse(
                farm_id=FARM_ID,
                schemes=[],
                evaluated_at=now,
            )
        ),
    )
    monkeypatch.setattr(
        "app.api.v1.market.MarketIntelligenceService.get_prices",
        AsyncMock(
            return_value=MarketPricesResponse(
                farm_id=FARM_ID,
                crop_type="WHEAT",
                prices=[],
                modal_trend="STABLE",
                as_of=now,
            )
        ),
    )
    monkeypatch.setattr(
        "app.api.v1.health_card.HealthCardService.get_health_card",
        AsyncMock(
            return_value=HealthCardResponse(
                farm_id=FARM_ID,
                crop_type="WHEAT",
                stage="Tillering",
                fsi=0.5,
                fsi_classification="MEDIUM_STRESS",
                soil_health_index=0.7,
                stress_momentum=_momentum(),
                yield_risk=_yield_risk(),
                health_score=62.0,
                health_band="FAIR",
                nearby_radar_high_count=0,
                unread_alerts=1,
                intelligence_snapshot_version="v3",
                explanation=explanation,
            )
        ),
    )
    monkeypatch.setattr(
        "app.api.v1.simulator.SimulatorService.run",
        AsyncMock(
            return_value=SimulatorResponse(
                farm_id=FARM_ID,
                baseline=SimulatorSnapshot(
                    fsi=0.5,
                    stress_momentum=_momentum(),
                    yield_risk=_yield_risk(),
                    fsi_curve=[0.5],
                    yield_factor=0.75,
                ),
                projected=SimulatorSnapshot(
                    fsi=0.65,
                    stress_momentum=_momentum(),
                    yield_risk=_yield_risk(),
                    fsi_curve=[0.5, 0.55, 0.6, 0.62, 0.65],
                    yield_factor=0.67,
                ),
                explanation=explanation,
                intelligence_snapshot_version="v3",
            )
        ),
    )

    return TestClient(app)


def test_optimizer_window_endpoint(client: TestClient) -> None:
    response = client.post(
        "/api/v1/optimizer/window",
        json={"farm_id": FARM_ID, "action_type": "SPRAY"},
    )
    assert response.status_code == 200
    assert response.json()["safe"] is False


def test_briefing_daily_endpoint(client: TestClient) -> None:
    response = client.get(f"/api/v1/briefing/daily?farm_id={FARM_ID}")
    assert response.status_code == 200
    assert response.json()["intelligence_snapshot_version"] == "v3"


def test_schemes_eligible_endpoint(client: TestClient) -> None:
    response = client.get(f"/api/v1/schemes/eligible?farm_id={FARM_ID}")
    assert response.status_code == 200


def test_market_prices_endpoint(client: TestClient) -> None:
    response = client.get(f"/api/v1/market/prices?farm_id={FARM_ID}")
    assert response.status_code == 200


def test_health_card_endpoint(client: TestClient) -> None:
    response = client.get(f"/api/v1/health-card?farm_id={FARM_ID}")
    assert response.status_code == 200
    body = response.json()
    assert body["stress_momentum"]["direction"] == "STABLE"
    assert body["yield_risk"]["risk_band"] == "MEDIUM"


def test_simulator_run_endpoint(client: TestClient) -> None:
    response = client.post(
        "/api/v1/simulator/run",
        json={"farm_id": FARM_ID, "temp_delta": 3.0},
    )
    assert response.status_code == 200
    assert response.json()["projected"]["fsi"] == 0.65


@pytest.mark.asyncio
async def test_get_latest_precompiled_briefing_success() -> None:
    from app.services.briefing_service import BriefingService
    
    db = MagicMock()
    # Mock get_owned_farm helper
    db.farms.find_one = AsyncMock(return_value={
        "_id": ObjectId(FARM_ID),
        "user_id": ObjectId(USER_ID),
        "location": {"coordinates": [77.5, 27.2]}
    })
    
    mock_log = {
        "_id": ObjectId(),
        "user_id": ObjectId(USER_ID),
        "farm_id": ObjectId(FARM_ID),
        "synthesis": "Test briefing summary",
        "language": "hi",
        "structured_sections": {
            "stress_momentum": {
                "direction": "STABLE",
                "momentum_score": 0.1,
                "fsi_delta": 0.02,
                "insufficient_history": False,
                "window_days": 7
            },
            "yield_risk": {
                "risk_band": "MEDIUM",
                "estimated_risk_percent": 45.0
            },
            "input_windows": {"SPRAY": False},
            "eligible_schemes_count": 1
        },
        "intelligence_snapshot_version": "v3",
        "generated_at": datetime.now(timezone.utc),
        "source": "WORKER"
    }
    
    db.briefing_logs.find_one = AsyncMock(return_value=mock_log)
    
    service = BriefingService(db)
    res = await service.get_latest_precompiled_briefing(USER_ID, FARM_ID)
    
    assert res.synthesis == "Test briefing summary"
    assert res.source == "WORKER"
    assert res.sections.eligible_schemes_count == 1

