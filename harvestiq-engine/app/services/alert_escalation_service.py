from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from zoneinfo import ZoneInfo

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.constants.alert_escalation import (
    CHANNEL_EMERGENCY_CONTACT,
    CHANNEL_IN_APP,
    CHANNEL_PUSH,
    CHANNEL_SMS,
    CONTACT_DELAY_CRITICAL_MINUTES,
    DEFAULT_QUIET_HOURS_END,
    DEFAULT_QUIET_HOURS_START,
    DEFAULT_TIMEZONE,
    ESCALATION_ACTIVE,
    ESCALATION_STOPPED,
    EVENT_ALERT_CREATED,
    EVENT_CONTACT_ESCALATION_FAILED,
    EVENT_CONTACT_ESCALATION_SENT,
    EVENT_ESCALATION_STOPPED,
    EVENT_IN_APP_DELIVERED,
    EVENT_PUSH_DEFERRED,
    EVENT_PUSH_DELIVERED,
    EVENT_PUSH_FAILED,
    EVENT_RETRY,
    EVENT_SEVERITY_ASSIGNED,
    EVENT_SMS_FAILED,
    EVENT_SMS_SENT,
    LIFECYCLE_ACKNOWLEDGED,
    LIFECYCLE_CREATED,
    LIFECYCLE_DELIVERED,
    LIFECYCLE_RESOLVED,
    PUSH_TIERS,
    QUIET_HOURS_TIERS,
    SMS_DELAY_CRITICAL_FARMER_MINUTES,
    SMS_DELAY_HIGH_MINUTES,
    STOP_REASON_ACKNOWLEDGED,
    STOP_REASON_RESOLVED,
    TERMINAL_LIFECYCLE,
)
from app.core.constants.alert_severity import SEVERITY_CRITICAL, SEVERITY_HIGH
from app.core.exceptions import forbidden, not_found
from app.integrations.sms_provider import TwilioProvider
from app.integrations.web_push_client import WebPushClient
from app.models.alert_escalation_schemas import (
    AlertPreferencesSchema,
    DeliveryEventResponse,
    EscalationHistoryResponse,
    EscalationStateResponse,
    EscalationTickResponse,
)


class AlertEscalationService:
    """
    Alert Escalation Engine — reads severity tier + lifecycle state, dispatches channels.
    Does NOT compute severity; stops immediately on ACKNOWLEDGED or RESOLVED.
    """

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self.db = db
        self.push_client = WebPushClient()
        self.sms_provider = TwilioProvider()

    async def start_for_alert(
        self,
        user_id: str,
        alert_id: str,
        farm_id: str,
        severity_tier: str,
    ) -> str:
        now = datetime.now(timezone.utc)
        prefs = await self._get_preferences(user_id)

        escalation_doc = {
            "alert_id": ObjectId(alert_id),
            "user_id": ObjectId(user_id),
            "farm_id": ObjectId(farm_id),
            "severity_tier": severity_tier,
            "status": ESCALATION_ACTIVE,
            "stop_reason": None,
            "push_sent": False,
            "push_sent_at": None,
            "push_deferred_until": None,
            "sms_farmer_due_at": self._schedule_sms_farmer(severity_tier, now),
            "sms_farmer_sent": False,
            "contacts_due_at": (
                now + timedelta(minutes=CONTACT_DELAY_CRITICAL_MINUTES)
                if severity_tier == SEVERITY_CRITICAL
                else None
            ),
            "contacts_sent": False,
            "created_at": now,
            "updated_at": now,
        }
        result = await self.db.alert_escalations.insert_one(escalation_doc)
        escalation_id = str(result.inserted_id)

        await self._log_event(
            alert_id=alert_id,
            escalation_id=escalation_id,
            user_id=user_id,
            event_type=EVENT_ALERT_CREATED,
            channel=CHANNEL_IN_APP,
            detail=f"Alert escalation started for tier {severity_tier}",
        )
        await self._log_event(
            alert_id=alert_id,
            escalation_id=escalation_id,
            user_id=user_id,
            event_type=EVENT_SEVERITY_ASSIGNED,
            channel=None,
            detail=f"Farm severity tier {severity_tier} assigned for escalation",
            metadata={"severity_tier": severity_tier},
        )

        await self.db.alerts.update_one(
            {"_id": ObjectId(alert_id)},
            {"$set": {"lifecycle_status": LIFECYCLE_DELIVERED}},
        )
        await self._log_event(
            alert_id=alert_id,
            escalation_id=escalation_id,
            user_id=user_id,
            event_type=EVENT_IN_APP_DELIVERED,
            channel=CHANNEL_IN_APP,
            detail="Alert delivered in-app",
        )

        if severity_tier in PUSH_TIERS and prefs.push_enabled:
            await self._try_push(user_id, alert_id, escalation_id, severity_tier, prefs, now)

        return escalation_id

    async def acknowledge_alert(self, alert_id: str, user_id: str) -> None:
        doc = await self._get_owned_alert(alert_id, user_id)
        if doc.get("lifecycle_status") in TERMINAL_LIFECYCLE:
            return

        now = datetime.now(timezone.utc)
        await self.db.alerts.update_one(
            {"_id": ObjectId(alert_id)},
            {
                "$set": {
                    "lifecycle_status": LIFECYCLE_ACKNOWLEDGED,
                    "acknowledged_at": now,
                    "acknowledged_by": ObjectId(user_id),
                    "read": True,
                }
            },
        )
        await self.stop_escalation(alert_id, STOP_REASON_ACKNOWLEDGED)

    async def resolve_alert(self, alert_id: str, user_id: str) -> None:
        await self._get_owned_alert(alert_id, user_id)
        now = datetime.now(timezone.utc)
        await self.db.alerts.update_one(
            {"_id": ObjectId(alert_id)},
            {
                "$set": {
                    "lifecycle_status": LIFECYCLE_RESOLVED,
                    "resolved_at": now,
                    "read": True,
                }
            },
        )
        await self.stop_escalation(alert_id, STOP_REASON_RESOLVED)

    async def stop_escalation(self, alert_id: str, reason: str) -> None:
        escalation = await self.db.alert_escalations.find_one(
            {"alert_id": ObjectId(alert_id), "status": ESCALATION_ACTIVE}
        )
        if escalation is None:
            return

        now = datetime.now(timezone.utc)
        await self.db.alert_escalations.update_one(
            {"_id": escalation["_id"]},
            {"$set": {"status": ESCALATION_STOPPED, "stop_reason": reason, "updated_at": now}},
        )
        await self._log_event(
            alert_id=alert_id,
            escalation_id=str(escalation["_id"]),
            user_id=str(escalation["user_id"]),
            event_type=EVENT_ESCALATION_STOPPED,
            channel=None,
            detail=f"Escalation stopped: {reason}",
            metadata={"stop_reason": reason},
        )

    async def process_tick(self, now: Optional[datetime] = None) -> EscalationTickResponse:
        now = now or datetime.now(timezone.utc)
        stats = EscalationTickResponse(
            processed=0, push_sent=0, sms_sent=0, contacts_sent=0, stopped=0, deferred=0
        )

        cursor = self.db.alert_escalations.find({"status": ESCALATION_ACTIVE})
        async for esc in cursor:
            stats.processed += 1
            alert = await self.db.alerts.find_one({"_id": esc["alert_id"]})
            if alert is None or alert.get("lifecycle_status") in TERMINAL_LIFECYCLE:
                await self._stop_doc(esc, STOP_REASON_ACKNOWLEDGED)
                stats.stopped += 1
                continue

            user_id = str(esc["user_id"])
            alert_id = str(esc["alert_id"])
            escalation_id = str(esc["_id"])
            tier = esc["severity_tier"]
            prefs = await self._get_preferences(user_id)

            # Deferred push
            if (
                not esc.get("push_sent")
                and esc.get("push_deferred_until")
                and esc["push_deferred_until"] <= now
            ):
                sent = await self._try_push(user_id, alert_id, escalation_id, tier, prefs, now)
                if sent:
                    stats.push_sent += 1
                else:
                    stats.deferred += 1

            # SMS to farmer
            if (
                prefs.sms_enabled
                and not esc.get("sms_farmer_sent")
                and esc.get("sms_farmer_due_at")
                and esc["sms_farmer_due_at"] <= now
                and tier in {SEVERITY_HIGH, SEVERITY_CRITICAL}
            ):
                if self._in_quiet_hours(tier, now, prefs):
                    stats.deferred += 1
                else:
                    ok = await self._send_farmer_sms(user_id, alert, escalation_id, alert_id)
                    if ok:
                        stats.sms_sent += 1
                        await self.db.alert_escalations.update_one(
                            {"_id": esc["_id"]},
                            {"$set": {"sms_farmer_sent": True, "updated_at": now}},
                        )

            # Emergency contacts — CRITICAL only
            if (
                tier == SEVERITY_CRITICAL
                and prefs.sms_enabled
                and not esc.get("contacts_sent")
                and esc.get("contacts_due_at")
                and esc["contacts_due_at"] <= now
            ):
                sent_count = await self._send_contact_sms(user_id, alert, escalation_id, alert_id)
                if sent_count > 0:
                    stats.contacts_sent += sent_count
                    await self.db.alert_escalations.update_one(
                        {"_id": esc["_id"]},
                        {"$set": {"contacts_sent": True, "updated_at": now}},
                    )

        return stats

    async def get_escalation_timeline(self, alert_id: str, user_id: str) -> EscalationStateResponse:
        await self._get_owned_alert(alert_id, user_id)
        escalation = await self.db.alert_escalations.find_one(
            {"alert_id": ObjectId(alert_id)},
            sort=[("created_at", -1)],
        )
        if escalation is None:
            raise not_found("Escalation record not found")

        events = await self._fetch_events(alert_id)
        return self._to_escalation_response(escalation, events)

    async def get_delivery_history(
        self, user_id: str, limit: int = 50
    ) -> EscalationHistoryResponse:
        cursor = (
            self.db.alert_delivery_events.find({"user_id": ObjectId(user_id)})
            .sort("recorded_at", -1)
            .limit(limit)
        )
        events: list[DeliveryEventResponse] = []
        async for doc in cursor:
            events.append(self._event_to_response(doc))
        total = await self.db.alert_delivery_events.count_documents(
            {"user_id": ObjectId(user_id)}
        )
        return EscalationHistoryResponse(events=events, total=total)

    async def save_push_subscription(self, user_id: str, subscription: dict[str, Any]) -> None:
        now = datetime.now(timezone.utc)
        await self.db.push_subscriptions.update_one(
            {"user_id": ObjectId(user_id), "endpoint": subscription["endpoint"]},
            {
                "$set": {
                    "user_id": ObjectId(user_id),
                    "endpoint": subscription["endpoint"],
                    "keys": subscription["keys"],
                    "updated_at": now,
                },
                "$setOnInsert": {"created_at": now},
            },
            upsert=True,
        )

    async def remove_push_subscription(self, user_id: str, endpoint: str) -> None:
        await self.db.push_subscriptions.delete_one(
            {"user_id": ObjectId(user_id), "endpoint": endpoint}
        )

    async def save_preferences(self, user_id: str, prefs: AlertPreferencesSchema) -> None:
        await self.db.users.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"alert_preferences": prefs.model_dump()}},
        )

    async def get_preferences(self, user_id: str) -> AlertPreferencesSchema:
        return await self._get_preferences(user_id)

    # --- internal helpers ---

    async def _try_push(
        self,
        user_id: str,
        alert_id: str,
        escalation_id: str,
        tier: str,
        prefs: AlertPreferencesSchema,
        now: datetime,
    ) -> bool:
        if tier not in PUSH_TIERS or not prefs.push_enabled:
            return False

        if self._in_quiet_hours(tier, now, prefs):
            defer_until = self._quiet_hours_end(now, prefs)
            await self.db.alert_escalations.update_one(
                {"_id": ObjectId(escalation_id)},
                {"$set": {"push_deferred_until": defer_until, "updated_at": now}},
            )
            await self._log_event(
                alert_id=alert_id,
                escalation_id=escalation_id,
                user_id=user_id,
                event_type=EVENT_PUSH_DEFERRED,
                channel=CHANNEL_PUSH,
                detail=f"Push deferred until quiet hours end ({defer_until.isoformat()})",
            )
            return False

        alert = await self.db.alerts.find_one({"_id": ObjectId(alert_id)})
        if alert is None:
            return False

        subscriptions = await self.db.push_subscriptions.find(
            {"user_id": ObjectId(user_id)}
        ).to_list(length=20)

        if not subscriptions:
            await self._log_event(
                alert_id=alert_id,
                escalation_id=escalation_id,
                user_id=user_id,
                event_type=EVENT_PUSH_FAILED,
                channel=CHANNEL_PUSH,
                detail="No push subscriptions registered",
            )
            return False

        any_success = False
        for sub in subscriptions:
            result = await self.push_client.send_notification(
                subscription={"endpoint": sub["endpoint"], "keys": sub["keys"]},
                title=alert.get("title", "HarvestIQ Alert"),
                body=alert.get("message", ""),
                data={"alert_id": alert_id, "farm_id": str(alert.get("farm_id", ""))},
            )
            if result["status"] == "DELIVERED":
                any_success = True
                await self._log_event(
                    alert_id=alert_id,
                    escalation_id=escalation_id,
                    user_id=user_id,
                    event_type=EVENT_PUSH_DELIVERED,
                    channel=CHANNEL_PUSH,
                    detail="Push notification delivered",
                    metadata={"mock": result.get("mock", False)},
                )
            else:
                await self._log_event(
                    alert_id=alert_id,
                    escalation_id=escalation_id,
                    user_id=user_id,
                    event_type=EVENT_PUSH_FAILED,
                    channel=CHANNEL_PUSH,
                    detail=result.get("error") or "Push delivery failed",
                )

        if any_success:
            await self.db.alert_escalations.update_one(
                {"_id": ObjectId(escalation_id)},
                {"$set": {"push_sent": True, "push_sent_at": now, "updated_at": now}},
            )
        return any_success

    async def _send_farmer_sms(
        self, user_id: str, alert: dict[str, Any], escalation_id: str, alert_id: str
    ) -> bool:
        user = await self.db.users.find_one({"_id": ObjectId(user_id)})
        phone = user.get("phone") if user else None
        if not phone:
            await self._log_event(
                alert_id=alert_id,
                escalation_id=escalation_id,
                user_id=user_id,
                event_type=EVENT_SMS_FAILED,
                channel=CHANNEL_SMS,
                detail="Farmer phone number not found",
            )
            return False

        body = f"HarvestIQ Alert: {alert.get('title', 'Field Alert')} — {alert.get('message', '')[:120]}"
        result = await self.sms_provider.send_sms(phone, body)
        if result.get("status") in {"SENT", "DELIVERED"}:
            await self._log_event(
                alert_id=alert_id,
                escalation_id=escalation_id,
                user_id=user_id,
                event_type=EVENT_SMS_SENT,
                channel=CHANNEL_SMS,
                detail="SMS sent to farmer",
                metadata={"message_sid": result.get("message_sid"), "to": phone[-4:]},
            )
            return True

        await self._log_event(
            alert_id=alert_id,
            escalation_id=escalation_id,
            user_id=user_id,
            event_type=EVENT_SMS_FAILED,
            channel=CHANNEL_SMS,
            detail=result.get("error") or "SMS delivery failed",
        )
        await self._log_event(
            alert_id=alert_id,
            escalation_id=escalation_id,
            user_id=user_id,
            event_type=EVENT_RETRY,
            channel=CHANNEL_SMS,
            detail="SMS delivery will retry on next tick",
        )
        return False

    async def _send_contact_sms(
        self, user_id: str, alert: dict[str, Any], escalation_id: str, alert_id: str
    ) -> int:
        """Emergency contacts — CRITICAL tier only. Never called for HIGH."""
        contacts_doc = await self.db.emergency_contacts.find_one({"user_id": ObjectId(user_id)})
        if not contacts_doc:
            await self._log_event(
                alert_id=alert_id,
                escalation_id=escalation_id,
                user_id=user_id,
                event_type=EVENT_CONTACT_ESCALATION_FAILED,
                channel=CHANNEL_EMERGENCY_CONTACT,
                detail="No emergency contacts configured",
            )
            return 0

        numbers = [
            contacts_doc.get("primary_contact"),
            contacts_doc.get("secondary_contact"),
            contacts_doc.get("village_contact"),
        ]
        numbers = [n for n in numbers if n]
        if not numbers:
            return 0

        body = (
            f"HarvestIQ CRITICAL: Farmer has an unread critical alert — "
            f"{alert.get('title', 'Field Alert')}. Please check on them."
        )
        sent = 0
        for phone in numbers:
            result = await self.sms_provider.send_sms(phone, body)
            if result.get("status") in {"SENT", "DELIVERED"}:
                sent += 1
                await self._log_event(
                    alert_id=alert_id,
                    escalation_id=escalation_id,
                    user_id=user_id,
                    event_type=EVENT_CONTACT_ESCALATION_SENT,
                    channel=CHANNEL_EMERGENCY_CONTACT,
                    detail=f"Emergency contact notified ({phone[-4:]})",
                    metadata={"message_sid": result.get("message_sid")},
                )
            else:
                await self._log_event(
                    alert_id=alert_id,
                    escalation_id=escalation_id,
                    user_id=user_id,
                    event_type=EVENT_CONTACT_ESCALATION_FAILED,
                    channel=CHANNEL_EMERGENCY_CONTACT,
                    detail=result.get("error") or f"Failed to notify {phone[-4:]}",
                )
        return sent

    async def _log_event(
        self,
        alert_id: str,
        escalation_id: Optional[str],
        user_id: str,
        event_type: str,
        channel: Optional[str],
        detail: str,
        metadata: Optional[dict[str, Any]] = None,
    ) -> None:
        now = datetime.now(timezone.utc)
        doc = {
            "alert_id": ObjectId(alert_id),
            "escalation_id": ObjectId(escalation_id) if escalation_id else None,
            "user_id": ObjectId(user_id),
            "event_type": event_type,
            "channel": channel,
            "detail": detail,
            "metadata": metadata or {},
            "recorded_at": now,
        }
        await self.db.alert_delivery_events.insert_one(doc)

    async def _get_owned_alert(self, alert_id: str, user_id: str) -> dict[str, Any]:
        if not ObjectId.is_valid(alert_id):
            raise not_found("Alert not found")
        doc = await self.db.alerts.find_one({"_id": ObjectId(alert_id)})
        if doc is None:
            raise not_found("Alert not found")
        if str(doc["user_id"]) != user_id:
            raise forbidden("You do not have access to this alert")
        return doc

    async def _get_preferences(self, user_id: str) -> AlertPreferencesSchema:
        user = await self.db.users.find_one({"_id": ObjectId(user_id)})
        raw = (user or {}).get("alert_preferences") or {}
        return AlertPreferencesSchema(**raw) if raw else AlertPreferencesSchema()

    async def _fetch_events(self, alert_id: str) -> list[DeliveryEventResponse]:
        cursor = (
            self.db.alert_delivery_events.find({"alert_id": ObjectId(alert_id)})
            .sort("recorded_at", 1)
        )
        return [self._event_to_response(doc) async for doc in cursor]

    async def _stop_doc(self, esc: dict[str, Any], reason: str) -> None:
        await self.db.alert_escalations.update_one(
            {"_id": esc["_id"]},
            {
                "$set": {
                    "status": ESCALATION_STOPPED,
                    "stop_reason": reason,
                    "updated_at": datetime.now(timezone.utc),
                }
            },
        )

    @staticmethod
    def _schedule_sms_farmer(tier: str, now: datetime) -> Optional[datetime]:
        if tier == SEVERITY_HIGH:
            return now + timedelta(minutes=SMS_DELAY_HIGH_MINUTES)
        if tier == SEVERITY_CRITICAL:
            return now + timedelta(minutes=SMS_DELAY_CRITICAL_FARMER_MINUTES)
        return None

    @staticmethod
    def _in_quiet_hours(tier: str, now: datetime, prefs: AlertPreferencesSchema) -> bool:
        if tier not in QUIET_HOURS_TIERS:
            return False
        try:
            tz = ZoneInfo(prefs.timezone or DEFAULT_TIMEZONE)
        except Exception:
            tz = ZoneInfo(DEFAULT_TIMEZONE)
        local = now.astimezone(tz)
        hour = local.hour
        start = prefs.quiet_hours_start if prefs.quiet_hours_start is not None else DEFAULT_QUIET_HOURS_START
        end = prefs.quiet_hours_end if prefs.quiet_hours_end is not None else DEFAULT_QUIET_HOURS_END
        if start > end:
            return hour >= start or hour < end
        return start <= hour < end

    @staticmethod
    def _quiet_hours_end(now: datetime, prefs: AlertPreferencesSchema) -> datetime:
        try:
            tz = ZoneInfo(prefs.timezone or DEFAULT_TIMEZONE)
        except Exception:
            tz = ZoneInfo(DEFAULT_TIMEZONE)
        local = now.astimezone(tz)
        end_hour = prefs.quiet_hours_end if prefs.quiet_hours_end is not None else DEFAULT_QUIET_HOURS_END
        target = local.replace(hour=end_hour, minute=0, second=0, microsecond=0)
        if target <= local:
            target += timedelta(days=1)
        return target.astimezone(timezone.utc)

    @staticmethod
    def _event_to_response(doc: dict[str, Any]) -> DeliveryEventResponse:
        recorded_at = doc["recorded_at"]
        if isinstance(recorded_at, datetime) and recorded_at.tzinfo is None:
            recorded_at = recorded_at.replace(tzinfo=timezone.utc)
        return DeliveryEventResponse(
            id=str(doc["_id"]),
            alert_id=str(doc["alert_id"]),
            escalation_id=str(doc["escalation_id"]) if doc.get("escalation_id") else None,
            event_type=doc["event_type"],
            channel=doc.get("channel"),
            detail=doc["detail"],
            metadata=doc.get("metadata", {}),
            recorded_at=recorded_at,
        )

    @staticmethod
    def _to_escalation_response(
        esc: dict[str, Any], events: list[DeliveryEventResponse]
    ) -> EscalationStateResponse:
        created_at = esc["created_at"]
        if isinstance(created_at, datetime) and created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        push_sent_at = esc.get("push_sent_at")
        if isinstance(push_sent_at, datetime) and push_sent_at.tzinfo is None:
            push_sent_at = push_sent_at.replace(tzinfo=timezone.utc)
        return EscalationStateResponse(
            id=str(esc["_id"]),
            alert_id=str(esc["alert_id"]),
            farm_id=str(esc["farm_id"]),
            severity_tier=esc["severity_tier"],
            status=esc["status"],
            stop_reason=esc.get("stop_reason"),
            push_sent=bool(esc.get("push_sent")),
            push_sent_at=push_sent_at,
            sms_farmer_sent=bool(esc.get("sms_farmer_sent")),
            contacts_sent=bool(esc.get("contacts_sent")),
            created_at=created_at,
            events=events,
        )
