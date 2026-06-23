from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.constants.alert_severity import (
    ADVISORY_PRIORITY_EMERGENCY,
    CRITICAL_FSI_WITH_CONFIRMED_DISEASE,
    CRITICAL_MIN_HIGH_ALERTS,
    FSI_HIGH_MIN,
    FSI_MEDIUM_MIN,
    RECENT_SOS_LOOKBACK_HOURS,
    SEVERITY_CRITICAL,
    SEVERITY_HIGH,
    SEVERITY_LOW,
    SEVERITY_MEDIUM,
    SEVERITY_RANK,
    TRIGGER_ADVISORY_EMERGENCY,
    TRIGGER_CONFIRMED_DISEASE_HIGH_FSI,
    TRIGGER_MULTIPLE_HIGH_ALERTS,
    TRIGGER_RECENT_SOS,
)
from app.core.constants.alerts import RULE_RAINFALL_DEFICIT
from app.core.constants.disease import DISEASE_STATUS_CONFIRMED, DISEASE_STATUS_POSSIBLE_DISEASE
from app.core.exceptions import not_found, unprocessable_entity
from app.models.alert_severity_schemas import AlertSeverityResult, AlertSeveritySignals
from app.models.engine_schemas import ExplanationPayload
from app.services.advisory_service import AdvisoryService
from app.services.explainability_service import build_alert_severity_explanation
from app.services.stress_index_service import StressIndexService


class AlertSeverityService:
    """
    Deterministic farm-level severity classification.
    Aggregates raw signals only — does not dispatch notifications.
    """

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self.db = db
        self.stress_service = StressIndexService(db)
        self.advisory_service = AdvisoryService(db)

    async def evaluate(
        self,
        user_id: str,
        farm_id: str,
        language: str = "en",
        persist: bool = True,
    ) -> AlertSeverityResult:
        if not ObjectId.is_valid(farm_id):
            raise unprocessable_entity("Invalid farm ID")

        farm = await self.db.farms.find_one(
            {"_id": ObjectId(farm_id), "user_id": ObjectId(user_id)}
        )
        if farm is None:
            raise not_found("Farm not found")

        signals = await self._collect_signals(user_id, farm_id, language)
        tier, critical_triggers, generated_because = self._classify(signals)
        explanation_payload = build_alert_severity_explanation(
            severity_tier=tier,
            generated_because=generated_because,
            critical_triggers=critical_triggers,
            signals=signals.model_dump(),
        )
        now = datetime.now(timezone.utc)
        result = AlertSeverityResult(
            farm_id=farm_id,
            severity_tier=tier,
            severity_rank=SEVERITY_RANK[tier],
            critical_triggers=critical_triggers,
            generated_because=generated_because,
            explanation=ExplanationPayload(**explanation_payload),
            signals=signals,
            evaluated_at=now,
        )

        if persist:
            log_id = await self._persist_log(user_id, farm_id, result)
            result.log_id = log_id

        return result

    async def get_latest(self, user_id: str, farm_id: str) -> Optional[AlertSeverityResult]:
        if not ObjectId.is_valid(farm_id):
            raise unprocessable_entity("Invalid farm ID")

        doc = await self.db.alert_severity_logs.find_one(
            {"user_id": ObjectId(user_id), "farm_id": ObjectId(farm_id)},
            sort=[("evaluated_at", -1)],
        )
        if doc is None:
            return None
        return self._doc_to_result(doc)

    async def _collect_signals(
        self,
        user_id: str,
        farm_id: str,
        language: str,
    ) -> AlertSeveritySignals:
        context = await self.stress_service.build_field_context(farm_id, user_id)
        stress_result = self.stress_service.calculate_fsi_from_context(context)

        latest_disease = await self.db.disease_reports.find_one(
            {"farm_id": ObjectId(farm_id)},
            sort=[("created_at", -1)],
        )
        confirmed_disease = False
        possible_or_confirmed = False
        disease_name: Optional[str] = None
        if latest_disease:
            status = str(latest_disease.get("deterministic_status", "")).upper()
            disease_name = (
                latest_disease.get("disease_name")
                or latest_disease.get("disease")
                or None
            )
            confirmed_disease = status == DISEASE_STATUS_CONFIRMED
            possible_or_confirmed = status in (
                DISEASE_STATUS_CONFIRMED,
                DISEASE_STATUS_POSSIBLE_DISEASE,
            )

        active_high = 0
        active_medium = 0
        active_low = 0
        active_rules: list[str] = []
        rainfall_deficit_active = False

        cursor = self.db.alerts.find(
            {"farm_id": ObjectId(farm_id), "user_id": ObjectId(user_id), "read": False}
        )
        async for alert in cursor:
            rule_id = str(alert.get("rule_id", ""))
            severity = str(alert.get("severity", "LOW")).upper()
            active_rules.append(rule_id)
            if severity == SEVERITY_HIGH:
                active_high += 1
            elif severity == SEVERITY_MEDIUM:
                active_medium += 1
            else:
                active_low += 1
            if rule_id == RULE_RAINFALL_DEFICIT:
                rainfall_deficit_active = True

        sos_cutoff = datetime.now(timezone.utc) - timedelta(hours=RECENT_SOS_LOOKBACK_HOURS)
        recent_sos = await self.db.sos_actions.find_one(
            {
                "user_id": ObjectId(user_id),
                "farm_id": ObjectId(farm_id),
                "triggered_at": {"$gte": sos_cutoff},
            }
        )

        advisory = await self.advisory_service.get_actions(user_id, farm_id, language)
        advisory_priority = str(advisory.priority).upper()

        return AlertSeveritySignals(
            fsi=round(stress_result.fsi, 4),
            fsi_classification=str(stress_result.classification),
            confirmed_disease=confirmed_disease,
            disease_name=disease_name,
            possible_or_confirmed_disease=possible_or_confirmed,
            active_high_alerts=active_high,
            active_medium_alerts=active_medium,
            active_low_alerts=active_low,
            active_alert_rules=active_rules,
            advisory_priority=advisory_priority,
            recent_sos=recent_sos is not None,
            weather_temp_c=round(context.weather.current.temp, 2),
            rainfall_deficit=round(stress_result.components.rainfall_deficit, 4),
            rainfall_deficit_alert_active=rainfall_deficit_active,
        )

    def _classify(
        self,
        signals: AlertSeveritySignals,
    ) -> tuple[str, list[str], list[str]]:
        critical_triggers: list[str] = []
        generated_because: list[str] = []

        if signals.confirmed_disease and signals.fsi > CRITICAL_FSI_WITH_CONFIRMED_DISEASE:
            critical_triggers.append(TRIGGER_CONFIRMED_DISEASE_HIGH_FSI)
            label = signals.disease_name or "Confirmed disease"
            generated_because.append(f"{label} detected (confirmed)")
            generated_because.append(f"FSI = {signals.fsi:.2f}")

        if signals.active_high_alerts >= CRITICAL_MIN_HIGH_ALERTS:
            critical_triggers.append(TRIGGER_MULTIPLE_HIGH_ALERTS)
            generated_because.append(
                f"{signals.active_high_alerts} HIGH alerts active simultaneously"
            )

        if signals.recent_sos:
            critical_triggers.append(TRIGGER_RECENT_SOS)
            generated_because.append("Manual SOS triggered in the last 24 hours")

        if signals.advisory_priority == ADVISORY_PRIORITY_EMERGENCY:
            critical_triggers.append(TRIGGER_ADVISORY_EMERGENCY)
            generated_because.append("Advisory Engine priority = EMERGENCY")

        base_tier = self._base_tier(signals)
        if critical_triggers:
            tier = SEVERITY_CRITICAL
        else:
            tier = base_tier

        if signals.rainfall_deficit_alert_active and "Rainfall Deficit active" not in " ".join(
            generated_because
        ):
            generated_because.append("Rainfall Deficit active")

        if signals.possible_or_confirmed_disease and not signals.confirmed_disease:
            name = signals.disease_name or "Possible disease"
            if f"{name} detected" not in " ".join(generated_because):
                generated_because.append(f"{name} detected (possible)")

        if signals.fsi >= FSI_MEDIUM_MIN and not any("FSI =" in g for g in generated_because):
            generated_because.append(f"FSI = {signals.fsi:.2f}")

        if signals.active_high_alerts == 1 and TRIGGER_MULTIPLE_HIGH_ALERTS not in critical_triggers:
            generated_because.append("HIGH severity field alert active")

        if signals.active_medium_alerts > 0:
            generated_because.append(f"{signals.active_medium_alerts} MEDIUM alert(s) active")

        if not generated_because:
            generated_because.append("All monitoring parameters within safe ranges")

        # Deduplicate while preserving order
        seen: set[str] = set()
        unique_because: list[str] = []
        for item in generated_because:
            if item not in seen:
                seen.add(item)
                unique_because.append(item)

        return tier, critical_triggers, unique_because

    @staticmethod
    def _base_tier(signals: AlertSeveritySignals) -> str:
        tier = SEVERITY_LOW

        if (
            signals.active_medium_alerts > 0
            or signals.rainfall_deficit_alert_active
            or (FSI_MEDIUM_MIN <= signals.fsi < FSI_HIGH_MIN)
        ):
            tier = SEVERITY_MEDIUM

        if (
            signals.active_high_alerts > 0
            or signals.fsi >= FSI_HIGH_MIN
            or signals.possible_or_confirmed_disease
        ):
            tier = SEVERITY_HIGH

        if signals.advisory_priority == SEVERITY_HIGH:
            tier = SEVERITY_HIGH
        elif signals.advisory_priority == SEVERITY_MEDIUM and tier == SEVERITY_LOW:
            tier = SEVERITY_MEDIUM

        return tier

    async def _persist_log(
        self,
        user_id: str,
        farm_id: str,
        result: AlertSeverityResult,
    ) -> str:
        doc: dict[str, Any] = {
            "user_id": ObjectId(user_id),
            "farm_id": ObjectId(farm_id),
            "severity_tier": result.severity_tier,
            "severity_rank": result.severity_rank,
            "critical_triggers": result.critical_triggers,
            "generated_because": result.generated_because,
            "explanation": result.explanation.model_dump(),
            "signals": result.signals.model_dump(),
            "evaluated_at": result.evaluated_at,
        }
        insert = await self.db.alert_severity_logs.insert_one(doc)
        return str(insert.inserted_id)

    @staticmethod
    def _doc_to_result(doc: dict[str, Any]) -> AlertSeverityResult:
        signals = AlertSeveritySignals(**doc.get("signals", {}))
        explanation_raw = doc.get("explanation", {})
        evaluated_at = doc.get("evaluated_at")
        if isinstance(evaluated_at, datetime) and evaluated_at.tzinfo is None:
            evaluated_at = evaluated_at.replace(tzinfo=timezone.utc)
        return AlertSeverityResult(
            farm_id=str(doc["farm_id"]),
            severity_tier=doc["severity_tier"],
            severity_rank=doc.get("severity_rank", SEVERITY_RANK.get(doc["severity_tier"], 1)),
            critical_triggers=list(doc.get("critical_triggers", [])),
            generated_because=list(doc.get("generated_because", [])),
            explanation=ExplanationPayload(**explanation_raw),
            signals=signals,
            evaluated_at=evaluated_at,
            log_id=str(doc["_id"]),
        )
