from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.constants.alerts import (
    ALERT_DEDUP_HOURS,
    ALERT_EXPIRE_DAYS,
    FSI_HIGH_ALERT_THRESHOLD,
    RAINFALL_DEFICIT_ALERT_THRESHOLD,
    RULE_FSI_HIGH,
    RULE_RAINFALL_DEFICIT,
    RULE_THERMAL_HIGH,
)
from app.core.exceptions import forbidden, not_found
from app.models.engine_schemas import (
    AlertResponse,
    AlertListResponse,
    TriggerEvaluationRequest,
    TriggerEvaluationResponse,
)
from app.core.constants.alert_escalation import LIFECYCLE_CREATED
from app.services.explainability_service import build_alert_explanation
from app.services.stress_index_service import FieldContext, StressIndexService


class AlertService:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self.db = db
        self.stress_service = StressIndexService(db)

    async def list_for_user(
        self,
        user_id: str,
        unread_only: bool = False,
        farm_id: Optional[str] = None,
        limit: int = 50,
        include_severity: bool = True,
    ) -> AlertListResponse:
        query: dict[str, Any] = {"user_id": ObjectId(user_id)}
        if unread_only:
            query["read"] = False
        if farm_id:
            if not ObjectId.is_valid(farm_id):
                raise not_found("Farm not found")
            query["farm_id"] = ObjectId(farm_id)

        cursor = self.db.alerts.find(query).sort("created_at", -1).limit(limit)
        alerts: list[AlertResponse] = []
        async for doc in cursor:
            alerts.append(self._to_alert_response(doc))

        unread_count = await self.db.alerts.count_documents(
            {"user_id": ObjectId(user_id), "read": False}
        )

        farm_severity = None
        if include_severity and farm_id:
            from app.services.alert_severity_service import AlertSeverityService

            severity_service = AlertSeverityService(self.db)
            latest = await severity_service.get_latest(user_id, farm_id)
            if latest is None:
                latest = await severity_service.evaluate(user_id, farm_id, persist=True)
            farm_severity = latest.model_dump(mode="json")

        return AlertListResponse(
            alerts=alerts,
            unread_count=unread_count,
            farm_severity=farm_severity,
        )

    async def mark_read(self, alert_id: str, user_id: str) -> AlertResponse:
        from app.services.alert_escalation_service import AlertEscalationService

        escalation = AlertEscalationService(self.db)
        await escalation.acknowledge_alert(alert_id, user_id)
        doc = await self.db.alerts.find_one({"_id": ObjectId(alert_id)})
        if doc is None:
            raise not_found("Alert not found")
        return self._to_alert_response(doc)

    async def acknowledge(self, alert_id: str, user_id: str) -> AlertResponse:
        return await self.mark_read(alert_id, user_id)

    async def resolve(self, alert_id: str, user_id: str) -> AlertResponse:
        from app.services.alert_escalation_service import AlertEscalationService

        escalation = AlertEscalationService(self.db)
        await escalation.resolve_alert(alert_id, user_id)
        doc = await self.db.alerts.find_one({"_id": ObjectId(alert_id)})
        if doc is None:
            raise not_found("Alert not found")
        return self._to_alert_response(doc)

    async def trigger_evaluation(
        self,
        user_id: str,
        payload: TriggerEvaluationRequest,
        language: str = "en",
    ) -> TriggerEvaluationResponse:
        context = await self.stress_service.build_field_context(payload.farm_id, user_id)
        stress_result = self.stress_service.calculate_fsi_from_context(context)
        triggered = await self._evaluate_and_persist(
            user_id=user_id,
            farm_id=payload.farm_id,
            context=context,
            stress_result=stress_result,
        )

        from app.services.alert_severity_service import AlertSeverityService

        severity_service = AlertSeverityService(self.db)
        severity_result = await severity_service.evaluate(
            user_id=user_id,
            farm_id=payload.farm_id,
            language=language,
            persist=True,
        )

        from app.services.alert_escalation_service import AlertEscalationService

        escalation_service = AlertEscalationService(self.db)
        for alert in triggered:
            await escalation_service.start_for_alert(
                user_id=user_id,
                alert_id=alert.id,
                farm_id=payload.farm_id,
                severity_tier=severity_result.severity_tier,
            )

        return TriggerEvaluationResponse(
            farm_id=payload.farm_id,
            evaluated_rules=3,
            triggered_count=len(triggered),
            alerts_created=triggered,
            cycle_status=context.cycle_status,
            severity=severity_result.model_dump(mode="json"),
        )

    async def _evaluate_and_persist(
        self,
        user_id: str,
        farm_id: str,
        context: FieldContext,
        stress_result: Any,
    ) -> list[AlertResponse]:
        rules = await self._load_enabled_rules()
        metrics = {
            "current_temp": context.weather.current.temp,
            "rainfall_deficit": stress_result.components.rainfall_deficit,
            "fsi": stress_result.fsi,
        }

        created: list[AlertResponse] = []
        for rule in rules:
            if not self._rule_passes(rule, metrics):
                continue

            alert = await self._persist_alert(
                user_id=user_id,
                farm_id=farm_id,
                rule=rule,
                metrics=metrics,
                stage=context.stage_name,
            )
            if alert is not None:
                created.append(alert)

        return created

    async def _load_enabled_rules(self) -> list[dict[str, Any]]:
        cursor = self.db.system_rules.find({"enabled": True})
        return [doc async for doc in cursor]

    def _rule_passes(self, rule: dict[str, Any], metrics: dict[str, float]) -> bool:
        rule_id = rule["rule_id"]
        if rule_id == RULE_THERMAL_HIGH:
            return metrics["current_temp"] > float(rule["threshold"])
        if rule_id == RULE_RAINFALL_DEFICIT:
            return metrics["rainfall_deficit"] >= RAINFALL_DEFICIT_ALERT_THRESHOLD
        if rule_id == RULE_FSI_HIGH:
            return metrics["fsi"] >= FSI_HIGH_ALERT_THRESHOLD
        return False

    async def _persist_alert(
        self,
        user_id: str,
        farm_id: str,
        rule: dict[str, Any],
        metrics: dict[str, float],
        stage: str,
    ) -> Optional[AlertResponse]:
        now = datetime.now(timezone.utc)
        dedup_key = f"{rule['rule_id']}:{farm_id}:{now.date().isoformat()}"

        existing = await self.db.alerts.find_one(
            {
                "dedup_key": dedup_key,
                "created_at": {"$gte": now - timedelta(hours=ALERT_DEDUP_HOURS)},
            }
        )
        if existing is not None:
            return None

        message = self._format_message(rule, metrics, stage)
        primary_factor = rule.get("primary_factor", "THERMAL")
        inputs = {
            "current_temp": round(metrics["current_temp"], 2),
            "rainfall_deficit": round(metrics["rainfall_deficit"], 4),
            "fsi": metrics["fsi"],
            "threshold": rule.get("threshold"),
            "stage": stage,
        }
        explanation = build_alert_explanation(
            rule["rule_id"],
            primary_factor,
            inputs,
            message,
        )

        doc = {
            "user_id": ObjectId(user_id),
            "farm_id": ObjectId(farm_id),
            "rule_id": rule["rule_id"],
            "severity": rule["severity"],
            "title": rule["title"],
            "message": message,
            "explanation": explanation,
            "read": False,
            "lifecycle_status": LIFECYCLE_CREATED,
            "acknowledged_at": None,
            "acknowledged_by": None,
            "resolved_at": None,
            "dedup_key": dedup_key,
            "created_at": now,
            "expires_at": now + timedelta(days=ALERT_EXPIRE_DAYS),
        }
        result = await self.db.alerts.insert_one(doc)
        doc["_id"] = result.inserted_id
        return self._to_alert_response(doc)

    @staticmethod
    def _format_message(rule: dict[str, Any], metrics: dict[str, float], stage: str) -> str:
        template = rule["message_template"]
        return template.format(
            current_temp=round(metrics["current_temp"], 1),
            rainfall_deficit=round(metrics["rainfall_deficit"], 2),
            fsi=metrics["fsi"],
            threshold=rule.get("threshold"),
            stage=stage,
        )

    @staticmethod
    def _to_alert_response(doc: dict[str, Any]) -> AlertResponse:
        created_at = doc["created_at"]
        if isinstance(created_at, datetime) and created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)

        return AlertResponse(
            id=str(doc["_id"]),
            farm_id=str(doc["farm_id"]),
            rule_id=doc["rule_id"],
            severity=doc["severity"],
            title=doc["title"],
            message=doc["message"],
            read=bool(doc.get("read", False)),
            lifecycle_status=doc.get("lifecycle_status", LIFECYCLE_CREATED),
            acknowledged_at=doc.get("acknowledged_at"),
            acknowledged_by=str(doc["acknowledged_by"]) if doc.get("acknowledged_by") else None,
            resolved_at=doc.get("resolved_at"),
            explanation=doc.get("explanation", {}),
            created_at=created_at,
        )
