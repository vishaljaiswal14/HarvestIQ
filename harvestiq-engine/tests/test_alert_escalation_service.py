from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from bson import ObjectId

from app.core.constants.alert_escalation import (
    ESCALATION_ACTIVE,
    ESCALATION_STOPPED,
    EVENT_CONTACT_ESCALATION_SENT,
    EVENT_ESCALATION_STOPPED,
    EVENT_PUSH_DEFERRED,
    EVENT_PUSH_DELIVERED,
    EVENT_SMS_SENT,
    LIFECYCLE_ACKNOWLEDGED,
    LIFECYCLE_DELIVERED,
    LIFECYCLE_RESOLVED,
    STOP_REASON_ACKNOWLEDGED,
    STOP_REASON_RESOLVED,
)
from app.core.constants.alert_severity import (
    SEVERITY_CRITICAL,
    SEVERITY_HIGH,
    SEVERITY_LOW,
    SEVERITY_MEDIUM,
)
from app.models.alert_escalation_schemas import AlertPreferencesSchema
from app.services.alert_escalation_service import AlertEscalationService

USER_ID = str(ObjectId())
FARM_ID = str(ObjectId())
ALERT_ID = str(ObjectId())


def _alert_doc(
    lifecycle: str = LIFECYCLE_DELIVERED,
    read: bool = False,
) -> dict:
    return {
        "_id": ObjectId(ALERT_ID),
        "user_id": ObjectId(USER_ID),
        "farm_id": ObjectId(FARM_ID),
        "title": "High temperature stress",
        "message": "Current temperature 41°C exceeds safe limit.",
        "lifecycle_status": lifecycle,
        "read": read,
    }


def _escalation_doc(
    tier: str = SEVERITY_HIGH,
    status: str = ESCALATION_ACTIVE,
    **extra,
) -> dict:
    now = datetime.now(timezone.utc)
    doc = {
        "_id": ObjectId(),
        "alert_id": ObjectId(ALERT_ID),
        "user_id": ObjectId(USER_ID),
        "farm_id": ObjectId(FARM_ID),
        "severity_tier": tier,
        "status": status,
        "stop_reason": None,
        "push_sent": False,
        "push_sent_at": None,
        "push_deferred_until": None,
        "sms_farmer_due_at": now - timedelta(minutes=1),
        "sms_farmer_sent": False,
        "contacts_due_at": now - timedelta(minutes=1) if tier == SEVERITY_CRITICAL else None,
        "contacts_sent": False,
        "created_at": now,
        "updated_at": now,
    }
    doc.update(extra)
    return doc


@pytest.fixture
def db() -> MagicMock:
    return MagicMock()


@pytest.fixture
def service(db: MagicMock) -> AlertEscalationService:
    svc = AlertEscalationService(db)
    svc.push_client.send_notification = AsyncMock(
        return_value={"status": "DELIVERED", "error": None, "mock": True}
    )
    svc.sms_provider.send_sms = AsyncMock(
        return_value={"status": "DELIVERED", "message_sid": "SM123", "error": None}
    )
    return svc


@pytest.mark.asyncio
async def test_start_for_alert_low_in_app_only(service: AlertEscalationService, db: MagicMock) -> None:
    db.alert_escalations.insert_one = AsyncMock(return_value=MagicMock(inserted_id=ObjectId()))
    db.alerts.update_one = AsyncMock()
    db.alert_delivery_events.insert_one = AsyncMock()
    db.users.find_one = AsyncMock(return_value={"_id": ObjectId(USER_ID)})
    db.push_subscriptions.find = MagicMock(
        return_value=MagicMock(to_list=AsyncMock(return_value=[]))
    )

    escalation_id = await service.start_for_alert(USER_ID, ALERT_ID, FARM_ID, SEVERITY_LOW)

    assert escalation_id
    db.alerts.update_one.assert_called()
    assert db.alert_delivery_events.insert_one.call_count >= 3
    service.push_client.send_notification.assert_not_called()


@pytest.mark.asyncio
async def test_start_for_alert_medium_sends_push(service: AlertEscalationService, db: MagicMock) -> None:
    esc_id = ObjectId()
    db.alert_escalations.insert_one = AsyncMock(return_value=MagicMock(inserted_id=esc_id))
    db.alert_escalations.update_one = AsyncMock()
    db.alerts.update_one = AsyncMock()
    db.alerts.find_one = AsyncMock(return_value=_alert_doc())
    db.alert_delivery_events.insert_one = AsyncMock()
    db.users.find_one = AsyncMock(return_value={"_id": ObjectId(USER_ID)})
    db.push_subscriptions.find = MagicMock(
        return_value=MagicMock(
            to_list=AsyncMock(
                return_value=[{"endpoint": "https://push.example/1", "keys": {"p256dh": "k", "auth": "a"}}]
            )
        )
    )

    with patch.object(service, "_in_quiet_hours", return_value=False):
        await service.start_for_alert(USER_ID, ALERT_ID, FARM_ID, SEVERITY_MEDIUM)

    service.push_client.send_notification.assert_called_once()
    db.alert_escalations.update_one.assert_called()


@pytest.mark.asyncio
async def test_acknowledge_stops_escalation(service: AlertEscalationService, db: MagicMock) -> None:
    esc = _escalation_doc()
    db.alerts.find_one = AsyncMock(return_value=_alert_doc())
    db.alerts.update_one = AsyncMock()
    db.alert_escalations.find_one = AsyncMock(return_value=esc)
    db.alert_escalations.update_one = AsyncMock()
    db.alert_delivery_events.insert_one = AsyncMock()

    await service.acknowledge_alert(ALERT_ID, USER_ID)

    db.alerts.update_one.assert_called_once()
    update = db.alerts.update_one.call_args[0][1]["$set"]
    assert update["lifecycle_status"] == LIFECYCLE_ACKNOWLEDGED
    assert update["read"] is True
    db.alert_escalations.update_one.assert_called_once()
    stop_update = db.alert_escalations.update_one.call_args[0][1]["$set"]
    assert stop_update["status"] == ESCALATION_STOPPED
    assert stop_update["stop_reason"] == STOP_REASON_ACKNOWLEDGED


@pytest.mark.asyncio
async def test_resolve_stops_escalation(service: AlertEscalationService, db: MagicMock) -> None:
    esc = _escalation_doc(tier=SEVERITY_CRITICAL)
    db.alerts.find_one = AsyncMock(return_value=_alert_doc())
    db.alerts.update_one = AsyncMock()
    db.alert_escalations.find_one = AsyncMock(return_value=esc)
    db.alert_escalations.update_one = AsyncMock()
    db.alert_delivery_events.insert_one = AsyncMock()

    await service.resolve_alert(ALERT_ID, USER_ID)

    update = db.alerts.update_one.call_args[0][1]["$set"]
    assert update["lifecycle_status"] == LIFECYCLE_RESOLVED
    stop_update = db.alert_escalations.update_one.call_args[0][1]["$set"]
    assert stop_update["stop_reason"] == STOP_REASON_RESOLVED


@pytest.mark.asyncio
async def test_tick_sends_sms_for_high_unread(service: AlertEscalationService, db: MagicMock) -> None:
    esc = _escalation_doc(tier=SEVERITY_HIGH)

    async def fake_find(_query):
        yield esc

    db.alert_escalations.find = MagicMock(return_value=fake_find({}))
    db.alerts.find_one = AsyncMock(return_value=_alert_doc())
    db.users.find_one = AsyncMock(return_value={"_id": ObjectId(USER_ID), "phone": "+919876543210"})
    db.alert_escalations.update_one = AsyncMock()
    db.alert_delivery_events.insert_one = AsyncMock()

    with patch.object(service, "_in_quiet_hours", return_value=False):
        result = await service.process_tick()

    assert result.sms_sent == 1
    service.sms_provider.send_sms.assert_called_once()


@pytest.mark.asyncio
async def test_tick_critical_sends_farmer_sms_after_5min(service: AlertEscalationService, db: MagicMock) -> None:
    esc = _escalation_doc(tier=SEVERITY_CRITICAL)

    async def fake_find(_query):
        yield esc

    db.alert_escalations.find = MagicMock(return_value=fake_find({}))
    db.alerts.find_one = AsyncMock(return_value=_alert_doc())
    db.users.find_one = AsyncMock(return_value={"_id": ObjectId(USER_ID), "phone": "+919876543210"})
    db.emergency_contacts.find_one = AsyncMock(
        return_value={"primary_contact": "+911111111111", "secondary_contact": "+912222222222"}
    )
    db.alert_escalations.update_one = AsyncMock()
    db.alert_delivery_events.insert_one = AsyncMock()

    with patch.object(service, "_in_quiet_hours", return_value=False):
        result = await service.process_tick()

    assert result.sms_sent == 1
    assert result.contacts_sent == 2


@pytest.mark.asyncio
async def test_high_never_notifies_emergency_contacts(service: AlertEscalationService, db: MagicMock) -> None:
    esc = _escalation_doc(tier=SEVERITY_HIGH, contacts_due_at=datetime.now(timezone.utc) - timedelta(minutes=1))

    async def fake_find(_query):
        yield esc

    db.alert_escalations.find = MagicMock(return_value=fake_find({}))
    db.alerts.find_one = AsyncMock(return_value=_alert_doc())
    db.users.find_one = AsyncMock(return_value={"_id": ObjectId(USER_ID), "phone": "+919876543210"})
    db.emergency_contacts.find_one = AsyncMock(
        return_value={"primary_contact": "+911111111111"}
    )
    db.alert_escalations.update_one = AsyncMock()
    db.alert_delivery_events.insert_one = AsyncMock()

    with patch.object(service, "_in_quiet_hours", return_value=False):
        result = await service.process_tick()

    assert result.contacts_sent == 0
    # Only farmer SMS — one call
    assert service.sms_provider.send_sms.call_count == 1


@pytest.mark.asyncio
async def test_quiet_hours_defers_push_for_high(service: AlertEscalationService, db: MagicMock) -> None:
    esc_id = ObjectId()
    db.alert_escalations.insert_one = AsyncMock(return_value=MagicMock(inserted_id=esc_id))
    db.alert_escalations.update_one = AsyncMock()
    db.alerts.update_one = AsyncMock()
    db.alerts.find_one = AsyncMock(return_value=_alert_doc())
    db.alert_delivery_events.insert_one = AsyncMock()
    db.users.find_one = AsyncMock(return_value={"_id": ObjectId(USER_ID)})
    db.push_subscriptions.find = MagicMock(
        return_value=MagicMock(
            to_list=AsyncMock(
                return_value=[{"endpoint": "https://push.example/1", "keys": {"p256dh": "k", "auth": "a"}}]
            )
        )
    )

    prefs = AlertPreferencesSchema(quiet_hours_start=22, quiet_hours_end=6)
    with patch.object(service, "_in_quiet_hours", return_value=True):
        with patch.object(service, "_quiet_hours_end", return_value=datetime.now(timezone.utc) + timedelta(hours=4)):
            await service.start_for_alert(USER_ID, ALERT_ID, FARM_ID, SEVERITY_HIGH)

    service.push_client.send_notification.assert_not_called()
    deferred_calls = [
        c for c in db.alert_delivery_events.insert_one.call_args_list
        if c[0][0].get("event_type") == EVENT_PUSH_DEFERRED
    ]
    assert len(deferred_calls) == 1


@pytest.mark.asyncio
async def test_critical_bypasses_quiet_hours_for_push(service: AlertEscalationService, db: MagicMock) -> None:
    esc_id = ObjectId()
    db.alert_escalations.insert_one = AsyncMock(return_value=MagicMock(inserted_id=esc_id))
    db.alert_escalations.update_one = AsyncMock()
    db.alerts.update_one = AsyncMock()
    db.alerts.find_one = AsyncMock(return_value=_alert_doc())
    db.alert_delivery_events.insert_one = AsyncMock()
    db.users.find_one = AsyncMock(return_value={"_id": ObjectId(USER_ID)})
    db.push_subscriptions.find = MagicMock(
        return_value=MagicMock(
            to_list=AsyncMock(
                return_value=[{"endpoint": "https://push.example/1", "keys": {"p256dh": "k", "auth": "a"}}]
            )
        )
    )

    # CRITICAL tier: _in_quiet_hours returns False (not in QUIET_HOURS_TIERS)
    await service.start_for_alert(USER_ID, ALERT_ID, FARM_ID, SEVERITY_CRITICAL)

    service.push_client.send_notification.assert_called_once()


@pytest.mark.asyncio
async def test_tick_stops_when_alert_acknowledged(service: AlertEscalationService, db: MagicMock) -> None:
    esc = _escalation_doc(tier=SEVERITY_CRITICAL)

    async def fake_find(_query):
        yield esc

    db.alert_escalations.find = MagicMock(return_value=fake_find({}))
    db.alerts.find_one = AsyncMock(return_value=_alert_doc(lifecycle=LIFECYCLE_ACKNOWLEDGED, read=True))
    db.alert_escalations.update_one = AsyncMock()
    db.alert_delivery_events.insert_one = AsyncMock()

    result = await service.process_tick()

    assert result.stopped == 1
    service.sms_provider.send_sms.assert_not_called()


@pytest.mark.asyncio
async def test_schedule_sms_high_30min_critical_5min() -> None:
    now = datetime(2026, 6, 23, 12, 0, tzinfo=timezone.utc)
    high_due = AlertEscalationService._schedule_sms_farmer(SEVERITY_HIGH, now)
    crit_due = AlertEscalationService._schedule_sms_farmer(SEVERITY_CRITICAL, now)
    assert high_due == now + timedelta(minutes=30)
    assert crit_due == now + timedelta(minutes=5)


@pytest.mark.asyncio
async def test_audit_trail_logged_on_start(service: AlertEscalationService, db: MagicMock) -> None:
    db.alert_escalations.insert_one = AsyncMock(return_value=MagicMock(inserted_id=ObjectId()))
    db.alert_escalations.update_one = AsyncMock()
    db.alerts.update_one = AsyncMock()
    db.alerts.find_one = AsyncMock(return_value=_alert_doc())
    db.alert_delivery_events.insert_one = AsyncMock()
    db.users.find_one = AsyncMock(return_value={})
    db.push_subscriptions.find = MagicMock(return_value=MagicMock(to_list=AsyncMock(return_value=[])))

    with patch.object(service, "_in_quiet_hours", return_value=False):
        await service.start_for_alert(USER_ID, ALERT_ID, FARM_ID, SEVERITY_MEDIUM)

    event_types = [call[0][0]["event_type"] for call in db.alert_delivery_events.insert_one.call_args_list]
    assert "ALERT_CREATED" in event_types
    assert "SEVERITY_ASSIGNED" in event_types
    assert "IN_APP_DELIVERED" in event_types


@pytest.mark.asyncio
async def test_save_push_subscription(db: MagicMock) -> None:
    service = AlertEscalationService(db)
    db.push_subscriptions.update_one = AsyncMock()
    await service.save_push_subscription(
        USER_ID,
        {"endpoint": "https://push.example/1", "keys": {"p256dh": "k", "auth": "a"}},
    )
    db.push_subscriptions.update_one.assert_called_once()
