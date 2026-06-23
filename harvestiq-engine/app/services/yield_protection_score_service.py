from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.constants.alert_severity import SEVERITY_RANK
from app.core.constants.disease import (
    DISEASE_STATUS_CONFIRMED_DISEASE,
    DISEASE_STATUS_HEALTHY,
    DISEASE_STATUS_POSSIBLE_DISEASE,
)
from app.core.constants.operations_copilot import PRIORITY_EMERGENCY, PRIORITY_HIGH
from app.core.constants.yield_protection import (
    ALERT_BURDEN_HIGH_PENALTY,
    ALERT_BURDEN_MEDIUM_PENALTY,
    BAND_AT_RISK,
    BAND_CRITICAL,
    BAND_MODERATE,
    BAND_PROTECTED,
    BAND_THRESHOLD_AT_RISK,
    BAND_THRESHOLD_MODERATE,
    BAND_THRESHOLD_PROTECTED,
    COMPLIANCE_BASE,
    COMPLIANCE_BONUS_CRITICAL_ACTION_COMPLETE,
    COMPLIANCE_BONUS_HIGH_ACTION_COMPLETE,
    COMPLIANCE_COMPLETION_LOOKBACK_DAYS,
    COMPLIANCE_PENALTY_INCOMPLETE_TODAY_ACTION,
    COMPLIANCE_PENALTY_STALE_CRITICAL_ALERT,
    COMPLIANCE_PENALTY_STALE_HIGH_ALERT,
    COMPLIANCE_STALE_ACTION_HOURS,
    COMPLIANCE_STALE_ALERT_HOURS,
    COMPONENT_MAX,
    LOSS_PREVENTION_BAND_HIGH,
    LOSS_PREVENTION_BAND_LOW,
    LOSS_PREVENTION_BAND_MODERATE,
    SEVERITY_RANK_PENALTY,
    TREND_DECLINING,
    TREND_DECLINING_DELTA,
    TREND_IMPROVING,
    TREND_IMPROVING_DELTA,
    TREND_LOOKBACK_DAYS,
    TREND_STABLE,
)
from app.core.exceptions import not_found, unprocessable_entity
from app.models.day6_schemas import CoreIntelligence
from app.models.engine_schemas import ExplanationPayload
from app.models.yield_protection_schemas import (
    YieldProtectionBreakdown,
    YieldProtectionHistoryResponse,
    YieldProtectionScoreResponse,
)


def _clamp(value: float, low: float = 0.0, high: float = COMPONENT_MAX) -> float:
    return max(low, min(high, value))


class YieldProtectionScoreService:
    """
    Computes farm Yield Protection Score (0–100) from existing engine outputs.
    Does not recompute FSI, disease detection, or alert severity rules.
    """

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self.db = db

    async def compute(
        self,
        user_id: str,
        farm_id: str,
        core: Optional[CoreIntelligence] = None,
        severity_tier: Optional[str] = None,
        persist: bool = True,
        language: str = "en",
    ) -> YieldProtectionScoreResponse:
        if not ObjectId.is_valid(farm_id):
            raise unprocessable_entity("Invalid farm ID")

        farm = await self.db.farms.find_one(
            {"_id": ObjectId(farm_id), "user_id": ObjectId(user_id)}
        )
        if farm is None:
            raise not_found("Farm not found")

        if core is None:
            from app.services.context_compiler_service import ContextCompilerService

            compiler = ContextCompilerService(self.db)
            core = await compiler._build_core_intelligence(user_id, farm_id)

        if severity_tier is None:
            from app.services.alert_severity_service import AlertSeverityService

            severity_tier = (
                await AlertSeverityService(self.db).evaluate(
                    user_id, farm_id, language=language, persist=False
                )
            ).severity_tier

        latest_disease = await self.db.disease_reports.find_one(
            {"farm_id": ObjectId(farm_id)}, sort=[("created_at", -1)]
        )
        unread_alerts = await self._load_unread_alerts(farm_id)
        completions = await self._load_recent_completions(user_id, farm_id)
        incomplete_today = await self._load_incomplete_today_actions(farm_id)

        disease_risk = self._disease_component(latest_disease)
        stress_risk = self._stress_component(core.fsi)
        alert_burden = self._alert_burden_component(unread_alerts, severity_tier)
        advisory_compliance = self._compliance_component(
            unread_alerts, completions, incomplete_today
        )

        breakdown = YieldProtectionBreakdown(
            disease_risk=round(disease_risk, 1),
            stress_risk=round(stress_risk, 1),
            alert_burden=round(alert_burden, 1),
            advisory_compliance=round(advisory_compliance, 1),
        )
        score = round(
            disease_risk + stress_risk + alert_burden + advisory_compliance, 1
        )
        band = self._score_band(score)
        trend, trend_delta = await self._compute_trend(farm_id, score)
        top_risk = self._top_risk(core, latest_disease, unread_alerts, severity_tier)
        loss_band = self._loss_prevention_band(unread_alerts, incomplete_today, severity_tier)
        risk_reduction = self._risk_reduction_narrative(loss_band, top_risk)

        now = datetime.now(timezone.utc)
        explanation = ExplanationPayload(
            summary=(
                f"Yield protection score is {score}/100 ({band}). "
                f"Top risk: {top_risk}."
            ),
            inputs={
                "breakdown": breakdown.model_dump(),
                "severity_tier": severity_tier,
                "fsi": core.fsi,
                "completed_actions": len(completions),
            },
            primary_factor=core.primary_factor,
        )

        log_id = None
        if persist:
            try:
                latest_log = await self.db.yield_protection_logs.find_one(
                    {"farm_id": ObjectId(farm_id)},
                    sort=[("calculated_at", -1)]
                )
            except TypeError:
                latest_log = None
            
            is_duplicate = False
            if latest_log:
                score_match = latest_log.get("score") == score
                band_match = latest_log.get("band") == band
                top_risk_match = latest_log.get("top_risk") == top_risk
                breakdown_match = latest_log.get("breakdown") == breakdown.model_dump()
                
                if score_match and band_match and top_risk_match and breakdown_match:
                    is_duplicate = True
                    log_id = str(latest_log["_id"])
                    
            if not is_duplicate:
                result = await self.db.yield_protection_logs.insert_one(
                    {
                        "user_id": ObjectId(user_id),
                        "farm_id": ObjectId(farm_id),
                        "score": score,
                        "band": band,
                        "breakdown": breakdown.model_dump(),
                        "trend": trend,
                        "trend_delta": trend_delta,
                        "top_risk": top_risk,
                        "potential_loss_prevention_band": loss_band,
                        "severity_tier": severity_tier,
                        "calculated_at": now,
                    }
                )
                log_id = str(result.inserted_id)

        return YieldProtectionScoreResponse(
            farm_id=farm_id,
            score=score,
            band=band,
            breakdown=breakdown,
            trend=trend,
            trend_delta=trend_delta,
            top_risk=top_risk,
            risk_reduction_impact=risk_reduction,
            potential_loss_prevention_band=loss_band,
            explanation=explanation,
            calculated_at=now,
            log_id=log_id,
        )

    async def get_history(
        self, user_id: str, farm_id: str, days: int = 30
    ) -> YieldProtectionHistoryResponse:
        if not ObjectId.is_valid(farm_id):
            raise unprocessable_entity("Invalid farm ID")
        since = datetime.now(timezone.utc) - timedelta(days=days)
        cursor = (
            self.db.yield_protection_logs.find(
                {
                    "farm_id": ObjectId(farm_id),
                    "user_id": ObjectId(user_id),
                    "calculated_at": {"$gte": since},
                }
            )
            .sort("calculated_at", 1)
        )
        entries = []
        async for doc in cursor:
            entries.append(
                {
                    "score": doc["score"],
                    "band": doc["band"],
                    "calculated_at": doc["calculated_at"].isoformat(),
                }
            )
        return YieldProtectionHistoryResponse(
            farm_id=farm_id, entries=entries, total=len(entries)
        )

    async def record_action_completion(
        self,
        user_id: str,
        farm_id: str,
        action_id: str,
        plan_id: str,
        priority: str,
    ) -> YieldProtectionScoreResponse:
        now = datetime.now(timezone.utc)
        await self.db.copilot_action_completions.update_one(
            {"action_id": action_id, "user_id": ObjectId(user_id)},
            {
                "$set": {
                    "farm_id": ObjectId(farm_id),
                    "plan_id": ObjectId(plan_id) if ObjectId.is_valid(plan_id) else plan_id,
                    "action_id": action_id,
                    "priority": priority,
                    "completed_at": now,
                }
            },
            upsert=True,
        )
        if ObjectId.is_valid(plan_id):
            await self.db.copilot_plans.update_one(
                {"_id": ObjectId(plan_id), "actions.id": action_id},
                {"$set": {"actions.$.completed": True, "updated_at": now}},
            )
        return await self.compute(user_id, farm_id, persist=True)

    @staticmethod
    def _disease_component(latest_disease: Optional[dict[str, Any]]) -> float:
        if latest_disease is None:
            return COMPONENT_MAX
        status = (latest_disease.get("deterministic_status") or "UNKNOWN").upper()
        if status == DISEASE_STATUS_HEALTHY:
            return COMPONENT_MAX
        if status == DISEASE_STATUS_POSSIBLE_DISEASE:
            return 10.0
        if status == DISEASE_STATUS_CONFIRMED_DISEASE:
            return 0.0
        return 18.0

    @staticmethod
    def _stress_component(fsi: float) -> float:
        return _clamp((1.0 - min(max(fsi, 0.0), 1.0)) * COMPONENT_MAX)

    @staticmethod
    def _alert_burden_component(
        unread_alerts: list[dict[str, Any]], severity_tier: str
    ) -> float:
        high_count = sum(1 for a in unread_alerts if a.get("severity") == "HIGH")
        medium_count = sum(1 for a in unread_alerts if a.get("severity") == "MEDIUM")
        rank = SEVERITY_RANK.get(severity_tier, 1)
        score = (
            COMPONENT_MAX
            - high_count * ALERT_BURDEN_HIGH_PENALTY
            - medium_count * ALERT_BURDEN_MEDIUM_PENALTY
            - (rank - 1) * SEVERITY_RANK_PENALTY
        )
        return _clamp(score)

    @staticmethod
    def _compliance_component(
        unread_alerts: list[dict[str, Any]],
        completions: list[dict[str, Any]],
        incomplete_today: list[dict[str, Any]],
    ) -> float:
        now = datetime.now(timezone.utc)
        score = COMPLIANCE_BASE

        for alert in unread_alerts:
            created = alert.get("created_at")
            if created is None:
                continue
            if isinstance(created, datetime) and created.tzinfo is None:
                created = created.replace(tzinfo=timezone.utc)
            age_hours = (now - created).total_seconds() / 3600
            if age_hours < COMPLIANCE_STALE_ALERT_HOURS:
                continue
            if alert.get("severity") in {"HIGH", "CRITICAL"}:
                score -= COMPLIANCE_PENALTY_STALE_CRITICAL_ALERT
            elif alert.get("severity") == "MEDIUM":
                score -= COMPLIANCE_PENALTY_STALE_HIGH_ALERT

        for action in incomplete_today:
            if action.get("completed"):
                continue
            if action.get("priority") not in {PRIORITY_HIGH, PRIORITY_EMERGENCY}:
                continue
            generated = action.get("generated_at")
            if generated is None:
                continue
            if isinstance(generated, datetime) and generated.tzinfo is None:
                generated = generated.replace(tzinfo=timezone.utc)
            age_hours = (now - generated).total_seconds() / 3600
            if age_hours >= COMPLIANCE_STALE_ACTION_HOURS:
                score -= COMPLIANCE_PENALTY_INCOMPLETE_TODAY_ACTION

        for completion in completions:
            priority = completion.get("priority", "MEDIUM")
            if priority == PRIORITY_EMERGENCY:
                score += COMPLIANCE_BONUS_CRITICAL_ACTION_COMPLETE
            elif priority == PRIORITY_HIGH:
                score += COMPLIANCE_BONUS_HIGH_ACTION_COMPLETE

        return _clamp(score)

    async def _load_unread_alerts(self, farm_id: str) -> list[dict[str, Any]]:
        cursor = self.db.alerts.find(
            {"farm_id": ObjectId(farm_id), "read": False}
        )
        return [doc async for doc in cursor]

    async def _load_recent_completions(
        self, user_id: str, farm_id: str
    ) -> list[dict[str, Any]]:
        since = datetime.now(timezone.utc) - timedelta(
            days=COMPLIANCE_COMPLETION_LOOKBACK_DAYS
        )
        cursor = self.db.copilot_action_completions.find(
            {
                "user_id": ObjectId(user_id),
                "farm_id": ObjectId(farm_id),
                "completed_at": {"$gte": since},
            }
        )
        return [doc async for doc in cursor]

    async def _load_incomplete_today_actions(
        self, farm_id: str
    ) -> list[dict[str, Any]]:
        plan = await self.db.copilot_plans.find_one(
            {"farm_id": ObjectId(farm_id)}, sort=[("generated_at", -1)]
        )
        if plan is None:
            return []
        generated_at = plan.get("generated_at")
        return [
            {**a, "generated_at": generated_at}
            for a in plan.get("actions", [])
            if a.get("horizon") == "TODAY" and not a.get("completed")
        ]

    async def _compute_trend(
        self, farm_id: str, current_score: float
    ) -> tuple[str, float]:
        since = datetime.now(timezone.utc) - timedelta(days=TREND_LOOKBACK_DAYS)
        prior = await self.db.yield_protection_logs.find_one(
            {
                "farm_id": ObjectId(farm_id),
                "calculated_at": {"$gte": since},
            },
            sort=[("calculated_at", 1)],
        )
        if prior is None:
            return TREND_STABLE, 0.0
        delta = round(current_score - prior["score"], 1)
        if delta >= TREND_IMPROVING_DELTA:
            return TREND_IMPROVING, delta
        if delta <= TREND_DECLINING_DELTA:
            return TREND_DECLINING, delta
        return TREND_STABLE, delta

    @staticmethod
    def _score_band(score: float) -> str:
        if score >= BAND_THRESHOLD_PROTECTED:
            return BAND_PROTECTED
        if score >= BAND_THRESHOLD_MODERATE:
            return BAND_MODERATE
        if score >= BAND_THRESHOLD_AT_RISK:
            return BAND_AT_RISK
        return BAND_CRITICAL

    @staticmethod
    def _top_risk(
        core: CoreIntelligence,
        latest_disease: Optional[dict[str, Any]],
        unread_alerts: list[dict[str, Any]],
        severity_tier: str,
    ) -> str:
        if latest_disease:
            status = (latest_disease.get("deterministic_status") or "").upper()
            if status == DISEASE_STATUS_CONFIRMED_DISEASE:
                name = latest_disease.get("disease_name") or latest_disease.get("disease") or "Disease"
                return f"Confirmed {name}"
        if core.fsi >= 0.65:
            return f"High field stress (FSI {int(core.fsi * 100)}%)"
        if unread_alerts:
            return unread_alerts[0].get("title", "Active field alert")
        if severity_tier in {"HIGH", "CRITICAL"}:
            return f"Farm severity tier: {severity_tier}"
        return "No significant risks detected"

    @staticmethod
    def _loss_prevention_band(
        unread_alerts: list[dict[str, Any]],
        incomplete_today: list[dict[str, Any]],
        severity_tier: str,
    ) -> str:
        high_priority_incomplete = sum(
            1
            for a in incomplete_today
            if a.get("priority") in {PRIORITY_HIGH, PRIORITY_EMERGENCY}
            and not a.get("completed")
        )
        if severity_tier == "CRITICAL" or high_priority_incomplete >= 2:
            return LOSS_PREVENTION_BAND_HIGH
        if unread_alerts or high_priority_incomplete >= 1 or severity_tier == "HIGH":
            return LOSS_PREVENTION_BAND_MODERATE
        return LOSS_PREVENTION_BAND_LOW

    @staticmethod
    def _risk_reduction_narrative(loss_band: str, top_risk: str) -> str:
        if loss_band == LOSS_PREVENTION_BAND_HIGH:
            return (
                f"High risk reduction impact: addressing today's actions may help prevent "
                f"significant loss related to {top_risk}. This is not an exact yield forecast."
            )
        if loss_band == LOSS_PREVENTION_BAND_MODERATE:
            return (
                f"Moderate potential loss prevention: timely action on {top_risk} "
                f"supports risk reduction. Outcomes depend on field conditions."
            )
        return (
            "Low immediate risk reduction needed. Continue preventive monitoring "
            "to maintain protection levels."
        )
