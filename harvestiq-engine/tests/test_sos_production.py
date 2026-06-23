from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from bson import ObjectId

from app.models.day7_schemas import SosTriggerRequest
from app.services.sos_service import SosService
from app.integrations.twilio_client import TwilioClient
from app.services.advisory_service import AdvisoryService
from app.models.day6_schemas import CoreIntelligence, StressMomentumResult, YieldRiskResult

@pytest.mark.asyncio
async def test_twilio_client_fallback(monkeypatch) -> None:
    client = TwilioClient()
    # By default in testing, Twilio credentials are empty/disabled
    monkeypatch.setattr(client.settings, "twilio_account_sid", "")
    res = await client.send_sms("9999999999", "Test Message")
    assert res["status"] == "QUEUED"
    assert "mock_twilio_sid" in res["message_sid"]
    assert res["error"] is None

@pytest.mark.asyncio
async def test_contacts_crud() -> None:
    db = MagicMock()
    user_id = str(ObjectId())
    
    # Mock find_one returning no contacts
    db.emergency_contacts.find_one = AsyncMock(return_value=None)
    service = SosService(db)
    
    contacts = await service.get_contacts(user_id)
    assert contacts["primary_contact"] == ""
    assert contacts["secondary_contact"] == ""
    assert contacts["village_contact"] == ""

    # Mock save update
    db.emergency_contacts.update_one = AsyncMock()
    saved = await service.save_contacts(user_id, {
        "primary_contact": "9876543210",
        "secondary_contact": "8765432109",
        "village_contact": "7654321098"
    })
    assert saved["primary_contact"] == "9876543210"
    db.emergency_contacts.update_one.assert_awaited_once()

@pytest.mark.asyncio
async def test_sos_dispatch_to_contacts(monkeypatch) -> None:
    db = MagicMock()
    user_id = str(ObjectId())
    farm_id = str(ObjectId())
    
    db.sos_actions.insert_one = AsyncMock(return_value=MagicMock(inserted_id=ObjectId()))
    db.users.find_one = AsyncMock(return_value={"phone": "9999999999", "name": "Demo Farmer"})
    db.farms.find_one = AsyncMock(return_value={"name": "Demo Farm", "state": "Rajasthan", "district": "Jaipur"})
    db.emergency_contacts.find_one = AsyncMock(return_value={
        "user_id": ObjectId(user_id),
        "primary_contact": "9876543210",
        "secondary_contact": "",
        "village_contact": "7654321098"
    })

    # Mock health snapshot
    core = MagicMock()
    core.stage = "Tillering"
    core.fsi = 0.82
    core.fsi_classification = "HIGH_STRESS"
    core.yield_risk.risk_band = "HIGH"
    
    snapshot = MagicMock()
    snapshot.core = core
    snapshot.health_band = "POOR"
    snapshot.unread_alerts = 2

    service = SosService(db)
    monkeypatch.setattr(service.context_compiler, "compile_health_snapshot", AsyncMock(return_value=snapshot))
    
    # Mock Twilio enabled and TwilioClient send_sms
    service.settings = MagicMock()
    service.settings.twilio_enabled = True
    
    sms_mock = AsyncMock(return_value={"status": "DELIVERED", "message_sid": "mock-sid", "error": None})
    monkeypatch.setattr(TwilioClient, "send_sms", sms_mock)

    result = await service.trigger(user_id, SosTriggerRequest(farm_id=farm_id, emergency_type="FLOOD"))
    
    assert result.delivery_status == "SENT"
    assert len(result.recipients) == 3  # Farmer + primary + village
    assert result.recipients[0].role == "farmer"
    assert result.recipients[1].role == "primary"
    assert result.recipients[2].role == "village"
    assert result.recipients[0].status == "DELIVERED"

@pytest.mark.asyncio
async def test_auto_sos_recommendation_card(monkeypatch) -> None:
    db = MagicMock()
    db.disease_reports.find_one = AsyncMock(return_value=None)
    
    mock_cursor = AsyncMock()
    mock_cursor.__aiter__ = lambda self: self
    mock_cursor.__anext__ = AsyncMock(side_effect=StopAsyncIteration)
    db.alerts.find = MagicMock(return_value=mock_cursor)

    service = AdvisoryService(db)
    
    # Mock field context
    field_context = MagicMock()
    field_context.weather.current.wind_speed = 10.0
    field_context.weather.current.temp = 25.0
    field_context.weather.current.humidity = 50.0
    field_context.weather.forecast = []
    monkeypatch.setattr(service.context_compiler.stress_service, "build_field_context", AsyncMock(return_value=field_context))
    
    # Mock core intelligence where Auto SOS is triggered:
    # FSI > 0.80, disease_present = True, yield_risk > 60%
    core_intel = CoreIntelligence(
        farm_id=str(ObjectId()),
        crop_type="WHEAT",
        stage="Tillering",
        fsi=0.85,
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
            risk_band="CRITICAL",
            estimated_risk_percent=75.0,
            contributing_factors=["FSI"],
        ),
        mitigation_locked=False,
        disease_present=True,
        radar_high_nearby=False,
        nearby_outbreaks=[],
        alert_rules=[],
        stage_vulnerability=0.5,
        cycle_status="ACTIVE",
    )
    monkeypatch.setattr(service.context_compiler, "_build_core_intelligence", AsyncMock(return_value=core_intel))
    
    actions = await service.get_actions(str(ObjectId()), str(ObjectId()), "en")
    
    assert actions.priority == "EMERGENCY"
    assert len(actions.today_actions) > 0
    sos_card = next((c for c in actions.today_actions if getattr(c, "is_sos", False)), None)
    assert sos_card is not None
    assert "Critical Farm Alert Detected" in sos_card.problem
    assert sos_card.is_sos is True


@pytest.mark.asyncio
async def test_sync_replay_save_contacts() -> None:
    from app.services.sync_service import SyncService
    from app.models.day7_schemas import SyncBatchRequest, SyncOperation
    
    db = MagicMock()
    db.sync_receipts.find_one = AsyncMock(return_value=None)
    db.sync_receipts.insert_one = AsyncMock()
    db.emergency_contacts.update_one = AsyncMock()
    
    service = SyncService(db)
    
    batch = SyncBatchRequest(operations=[
        SyncOperation(
            client_id="contacts-123",
            operation_type="SAVE_EMERGENCY_CONTACTS",
            payload={
                "primary_contact": "9999999999",
                "secondary_contact": "8888888888",
                "village_contact": "7777777777"
            },
            client_timestamp=datetime.now(timezone.utc)
        )
    ])
    
    res = await service.replay_batch(str(ObjectId()), batch)
    assert res.processed == 1
    assert res.results[0].status == "SUCCESS"
    db.emergency_contacts.update_one.assert_awaited_once()
