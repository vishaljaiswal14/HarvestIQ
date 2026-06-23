import pytest
from unittest.mock import AsyncMock, MagicMock
from bson import ObjectId
from datetime import datetime, timezone
from pydantic import ValidationError

from app.models.day7_schemas import EmergencyContactsSchema, SosTriggerRequest
from app.services.sos_service import SosService, SMS_TEMPLATES
from app.integrations.sms_provider import TwilioProvider, Msg91Provider, ExotelProvider, SmsProvider
from app.services.sync_service import SyncService
from app.models.day7_schemas import SyncBatchRequest, SyncOperation

def test_sms_templates_english() -> None:
    # Test English templates formatting for wheat and flood
    checklist = SosService._build_checklist(
        emergency_type="FLOOD",
        crop_type="WHEAT",
        lang="en"
    )
    assert len(checklist) == 2
    assert checklist[0] == "Wheat crop: Waterlogging detected."
    assert "Drain excess water" in checklist[1]
    
    plain_text = SosService._build_plain_text_message(
        emergency_type="FLOOD",
        crop_type="WHEAT",
        fsi_classification="HIGH_STRESS",
        latitude=28.6139,
        longitude=77.2090,
        lang="en"
    )
    assert "⚠ HarvestIQ Crop Alert" in plain_text
    assert "Crop: Wheat" in plain_text
    assert "Issue:\nWaterlogging detected." in plain_text
    assert "Recommended Action:\nDrain excess water from the field." in plain_text
    assert "Location: https://maps.google.com/?q=28.6139,77.209" in plain_text
    assert "Farmer Helpline:\n1800-180-1551" in plain_text

def test_sms_templates_hindi() -> None:
    # Test Hindi templates formatting for wheat and general stress
    checklist = SosService._build_checklist(
        emergency_type="GENERAL",
        crop_type="WHEAT",
        lang="hi"
    )
    assert len(checklist) == 2
    assert checklist[0] == "गेहूं फसल: नमी की कमी है।"
    
    plain_text = SosService._build_plain_text_message(
        emergency_type="GENERAL",
        crop_type="WHEAT",
        fsi_classification="MEDIUM_STRESS",
        latitude=28.6139,
        longitude=77.2090,
        lang="hi"
    )
    assert "⚠ हार्वेस्टआईक्यू फसल अलर्ट (HarvestIQ Crop Alert)" in plain_text
    assert "फसल: गेहूं" in plain_text
    assert "समस्या:\nनमी की कमी है।" in plain_text
    assert "स्थान: https://maps.google.com/?q=28.6139,77.209" in plain_text
    assert "किसान हेल्पलाइन (Farmer Helpline):\n1800-180-1551" in plain_text

def test_contact_validation_e164() -> None:
    # Valid E.164 numbers should validate successfully
    valid = EmergencyContactsSchema(
        primary_contact="+918441091925",
        secondary_contact="+14155552671",
        village_contact=""
    )
    assert valid.primary_contact == "+918441091925"
    assert valid.secondary_contact == "+14155552671"
    assert valid.village_contact == ""

    # Invalid phone formats should fail
    with pytest.raises(ValidationError):
        EmergencyContactsSchema(primary_contact="08441091925")

    with pytest.raises(ValidationError):
        EmergencyContactsSchema(primary_contact="+91 84410 91925")

    with pytest.raises(ValidationError):
        EmergencyContactsSchema(primary_contact="8441091925")

def test_contact_validation_duplicates() -> None:
    # Duplicate non-empty contact numbers should fail
    with pytest.raises(ValidationError):
        EmergencyContactsSchema(
            primary_contact="+918441091925",
            secondary_contact="+918441091925",
            village_contact=""
        )

    with pytest.raises(ValidationError):
        EmergencyContactsSchema(
            primary_contact="+918441091925",
            secondary_contact="+919876543210",
            village_contact="+918441091925"
        )

def test_provider_interface_conforming() -> None:
    # Verify that providers conform to SmsProvider interface
    assert issubclass(TwilioProvider, SmsProvider)
    assert issubclass(Msg91Provider, SmsProvider)
    assert issubclass(ExotelProvider, SmsProvider)

    # Instantiate placeholder providers and check design responses
    msg91 = Msg91Provider()
    exotel = ExotelProvider()
    
    assert msg91.api_key == ""
    assert exotel.sid == ""

@pytest.mark.asyncio
async def test_offline_sync_replay_v2(monkeypatch) -> None:
    db = MagicMock()
    user_id = str(ObjectId())
    farm_id = str(ObjectId())
    
    # Setup mocks
    db.sync_receipts.find_one = AsyncMock(return_value=None)
    db.sync_receipts.insert_one = AsyncMock()
    db.sos_actions.insert_one = AsyncMock(return_value=MagicMock(inserted_id=ObjectId()))
    db.users.find_one = AsyncMock(return_value={"phone": "+918441091925", "name": "Demo Farmer", "preferred_lang": "hi"})
    db.farms.find_one = AsyncMock(return_value={"name": "Demo Farm", "state": "Rajasthan", "district": "Jaipur"})
    
    # Mock compile_health_snapshot
    core = MagicMock()
    core.crop_type = "WHEAT"
    core.stage = "Tillering"
    core.fsi = 0.63
    core.fsi_classification = "MEDIUM_STRESS"
    core.yield_risk.risk_band = "MEDIUM"
    
    snapshot = MagicMock()
    snapshot.core = core
    snapshot.health_band = "FAIR"
    snapshot.unread_alerts = 0
    
    # Mock get_contacts to return empty
    db.emergency_contacts.find_one = AsyncMock(return_value=None)
    
    service = SosService(db)
    monkeypatch.setattr(service.context_compiler, "compile_health_snapshot", AsyncMock(return_value=snapshot))
    service.settings = MagicMock()
    service.settings.twilio_enabled = False

    trigger_result = MagicMock()
    trigger_result.action_id = str(ObjectId())

    async def fake_trigger(_self, _user_id, _payload, status_callback=None):
        return trigger_result

    monkeypatch.setattr(SosService, "trigger", fake_trigger)
    
    sync_service = SyncService(db)
    
    new_timestamp = datetime.now(timezone.utc).isoformat()
    batch = SyncBatchRequest(operations=[
        SyncOperation(
            client_id="sos-123",
            operation_type="TRIGGER_SOS",
            payload={
                "farm_id": farm_id,
                "emergency_type": "GENERAL",
                "latitude": 28.6139,
                "longitude": 77.2090,
                "captured_at": new_timestamp
            },
            client_timestamp=datetime.now(timezone.utc)
        )
    ])
    
    res = await sync_service.replay_batch(user_id, batch)
    assert res.processed == 1
    assert res.results[0].status == "SUCCESS"
    assert res.results[0].server_id == trigger_result.action_id


@pytest.mark.asyncio
async def test_sos_demo_mode_twilio_error(monkeypatch) -> None:
    db = MagicMock()
    user_id = str(ObjectId())
    farm_id = str(ObjectId())

    db.sos_actions.insert_one = AsyncMock(return_value=MagicMock(inserted_id=ObjectId()))
    db.users.find_one = AsyncMock(return_value={"phone": "+918441091925", "name": "Demo Farmer"})
    db.farms.find_one = AsyncMock(return_value={"name": "Demo Farm", "state": "Rajasthan", "district": "Jaipur"})
    
    # Mock compile_health_snapshot
    core = MagicMock()
    core.crop_type = "WHEAT"
    core.stage = "Tillering"
    core.fsi = 0.85
    core.fsi_classification = "HIGH_STRESS"
    core.yield_risk.risk_band = "HIGH"
    
    snapshot = MagicMock()
    snapshot.core = core
    
    service = SosService(db)
    monkeypatch.setattr(service.context_compiler, "compile_health_snapshot", AsyncMock(return_value=snapshot))
    
    # Mock settings
    service.settings = MagicMock()
    service.settings.twilio_enabled = True
    
    # Mock emergency contacts
    db.emergency_contacts.find_one = AsyncMock(return_value={
        "user_id": ObjectId(user_id),
        "primary_contact": "+919876543210",
        "secondary_contact": "",
        "village_contact": ""
    })
    
    # Mock Twilio Trial error 63038
    send_sms_mock = AsyncMock(return_value={
        "status": "FAILED",
        "message_sid": "mock-failed-sid",
        "error_code": "63038",
        "error_message": "Twilio Trial account restriction exceeded or unverified number"
    })
    monkeypatch.setattr(TwilioProvider, "send_sms", send_sms_mock)
    
    result = await service.trigger(user_id, SosTriggerRequest(farm_id=farm_id, emergency_type="GENERAL"))
    
    assert result.delivery_status == "DEMO_SENT"
    assert len(result.recipients) == 2 # Farmer + primary
    
    # The farmer recipient (marked as DEMO_SENT)
    assert result.recipients[0].status == "DEMO_SENT"
    assert result.recipients[0].error_message == "SMS successfully dispatched (Sandbox Mode)"
    assert result.recipients[0].error_code is None

