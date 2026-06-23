import hashlib
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.constants.alert_severity import SEVERITY_RANK
from app.core.constants.copilot_explainability import (
    DEFAULT_EXPECTED_BENEFIT,
    DEFAULT_IF_IGNORED,
    EXPLAIN_AUTO_SOS,
    EXPLAIN_DISEASE_CONFIRMED,
    EXPLAIN_DISEASE_POSSIBLE,
    EXPLAIN_FSI_HIGH,
    EXPLAIN_FSI_MEDIUM,
    EXPLAIN_HUMIDITY_RUST,
    EXPLAIN_PREVENTIVE_SCOUTING,
    EXPLAIN_RAINFALL_DEFICIT,
    EXPLAIN_ROUTINE_HEALTHY,
    EXPLAIN_THERMAL_HIGH,
)
from app.core.constants.operations_copilot import (
    CARD_GREEN,
    CARD_RED,
    CARD_YELLOW,
    HORIZON_PREVENTIVE,
    HORIZON_THIS_WEEK,
    HORIZON_TODAY,
    PRIORITY_EMERGENCY,
    PRIORITY_HIGH,
    PRIORITY_LOW,
    PRIORITY_MEDIUM,
    PRIORITY_RANK,
)
from app.core.exceptions import not_found, unprocessable_entity
from app.models.day8_schemas_actions import ActionCard, AdvisoryActionsResponse
from app.models.operations_copilot_schemas import (
    CopilotAction,
    CopilotActionCompleteResponse,
    OperationsCopilotResponse,
)
from app.services.advisory_service import AdvisoryService
from app.services.yield_protection_score_service import YieldProtectionScoreService


class OperationsCopilotService:
    """
    Orchestrates farm operations plans from existing engines only.
    Does NOT duplicate disease, FSI, or alert severity logic.
    """

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self.db = db
        self.advisory_service = AdvisoryService(db)
        self.score_service = YieldProtectionScoreService(db)

    async def generate_plan(
        self,
        user_id: str,
        farm_id: str,
        language: str = "en",
        persist: bool = True,
    ) -> OperationsCopilotResponse:
        if not ObjectId.is_valid(farm_id):
            raise unprocessable_entity("Invalid farm ID")

        from app.services.alert_severity_service import AlertSeverityService
        from app.services.context_compiler_service import ContextCompilerService

        compiler = ContextCompilerService(self.db)
        core = await compiler._build_core_intelligence(user_id, farm_id)
        severity = await AlertSeverityService(self.db).evaluate(
            user_id, farm_id, language=language, persist=persist
        )
        advisory = await self.advisory_service.get_actions(user_id, farm_id, language)
        field_context = await compiler.stress_service.build_field_context(farm_id, user_id)

        ctx = self._build_explain_context(core, severity, advisory, field_context)
        completed_ids = await self._completed_action_ids(user_id, farm_id)

        today: list[CopilotAction] = []
        this_week: list[CopilotAction] = []
        preventive: list[CopilotAction] = []

        for card in advisory.today_actions:
            action = self._card_to_copilot_action(
                card, HORIZON_TODAY, advisory.priority, ctx, completed_ids
            )
            today.append(action)

        for card in advisory.this_week_actions:
            if card.card_type == CARD_GREEN and not advisory.today_actions:
                preventive.append(
                    self._card_to_copilot_action(
                        card, HORIZON_PREVENTIVE, PRIORITY_LOW, ctx, completed_ids
                    )
                )
            else:
                this_week.append(
                    self._card_to_copilot_action(
                        card, HORIZON_THIS_WEEK, advisory.priority, ctx, completed_ids
                    )
                )

        preventive.extend(self._preventive_actions(core, field_context, ctx, completed_ids))

        priority = self._resolve_priority(advisory.priority, severity.severity_tier)
        all_actions = today + this_week + preventive
        loss_band = self.score_service._loss_prevention_band(
            await self.score_service._load_unread_alerts(farm_id),
            [a.model_dump() for a in today if not a.completed],
            severity.severity_tier,
        )
        risk_reduction = self.score_service._risk_reduction_narrative(
            loss_band, self.score_service._top_risk(
                core, await self.db.disease_reports.find_one(
                    {"farm_id": ObjectId(farm_id)}, sort=[("created_at", -1)]
                ),
                await self.score_service._load_unread_alerts(farm_id),
                severity.severity_tier,
            )
        )

        now = datetime.now(timezone.utc)
        plan_id = str(ObjectId())
        if persist:
            try:
                latest_plan = await self.db.copilot_plans.find_one(
                    {"farm_id": ObjectId(farm_id)},
                    sort=[("generated_at", -1)]
                )
            except TypeError:
                latest_plan = None
            
            is_duplicate = False
            if latest_plan:
                crop_match = latest_plan.get("crop_type") == core.crop_type
                stage_match = latest_plan.get("stage") == core.stage
                priority_match = latest_plan.get("priority") == priority
                severity_match = latest_plan.get("severity_tier") == severity.severity_tier
                summary_match = latest_plan.get("situation_summary") == advisory.situation_summary
                
                curr_actions_dump = [a.model_dump(mode="json") for a in all_actions]
                prev_actions_dump = latest_plan.get("actions", [])
                
                def make_comparable(actions):
                    return sorted([
                        (a.get("id"), a.get("title"), a.get("action"), a.get("horizon"))
                        for a in actions
                    ], key=lambda x: x[0] or "")
                
                actions_match = make_comparable(curr_actions_dump) == make_comparable(prev_actions_dump)
                
                if crop_match and stage_match and priority_match and severity_match and summary_match and actions_match:
                    is_duplicate = True
                    plan_id = str(latest_plan["_id"])
                    
            if not is_duplicate:
                doc = {
                    "_id": ObjectId(plan_id),
                    "user_id": ObjectId(user_id),
                    "farm_id": ObjectId(farm_id),
                    "crop_type": core.crop_type,
                    "stage": core.stage,
                    "priority": priority,
                    "severity_tier": severity.severity_tier,
                    "situation_summary": advisory.situation_summary,
                    "actions": [a.model_dump(mode="json") for a in all_actions],
                    "risk_reduction_impact": risk_reduction,
                    "potential_loss_prevention_band": loss_band,
                    "why_generated": advisory.why_generated + severity.generated_because,
                    "generated_at": now,
                }
                await self.db.copilot_plans.insert_one(doc)

        score_result = await self.score_service.compute(
            user_id,
            farm_id,
            core=core,
            severity_tier=severity.severity_tier,
            persist=persist,
            language=language,
        )

        return OperationsCopilotResponse(
            farm_id=farm_id,
            crop_type=core.crop_type,
            stage=core.stage,
            priority=priority,
            severity_tier=severity.severity_tier,
            situation_summary=advisory.situation_summary,
            today_actions=today,
            this_week_actions=this_week,
            preventive_actions=preventive,
            risk_reduction_impact=risk_reduction,
            potential_loss_prevention_band=loss_band,
            why_generated=advisory.why_generated + severity.generated_because,
            generated_at=now,
            plan_id=plan_id,
            yield_protection_score=score_result.score,
            yield_protection_band=score_result.band,
        )

    async def get_latest_plan(
        self, user_id: str, farm_id: str
    ) -> OperationsCopilotResponse:
        if not ObjectId.is_valid(farm_id):
            raise unprocessable_entity("Invalid farm ID")
        doc = await self.db.copilot_plans.find_one(
            {"farm_id": ObjectId(farm_id), "user_id": ObjectId(user_id)},
            sort=[("generated_at", -1)],
        )
        if doc is None:
            return await self.generate_plan(user_id, farm_id, persist=True)

        today, this_week, preventive = [], [], []
        for raw in doc.get("actions", []):
            action = CopilotAction(**raw)
            if action.horizon == HORIZON_TODAY:
                today.append(action)
            elif action.horizon == HORIZON_THIS_WEEK:
                this_week.append(action)
            else:
                preventive.append(action)

        score_doc = await self.db.yield_protection_logs.find_one(
            {"farm_id": ObjectId(farm_id)}, sort=[("calculated_at", -1)]
        )
        return OperationsCopilotResponse(
            farm_id=farm_id,
            crop_type=doc.get("crop_type", ""),
            stage=doc.get("stage", ""),
            priority=doc.get("priority", PRIORITY_LOW),
            severity_tier=doc.get("severity_tier", "LOW"),
            situation_summary=doc.get("situation_summary", ""),
            today_actions=today,
            this_week_actions=this_week,
            preventive_actions=preventive,
            risk_reduction_impact=doc.get("risk_reduction_impact", ""),
            potential_loss_prevention_band=doc.get(
                "potential_loss_prevention_band", "LOW"
            ),
            why_generated=doc.get("why_generated", []),
            generated_at=doc["generated_at"],
            plan_id=str(doc["_id"]),
            yield_protection_score=score_doc["score"] if score_doc else None,
            yield_protection_band=score_doc["band"] if score_doc else None,
        )

    async def complete_action(
        self, user_id: str, farm_id: str, action_id: str, plan_id: str
    ) -> CopilotActionCompleteResponse:
        plan = await self.db.copilot_plans.find_one(
            {
                "_id": ObjectId(plan_id),
                "farm_id": ObjectId(farm_id),
                "user_id": ObjectId(user_id),
            }
        )
        if plan is None:
            raise not_found("Plan not found")

        priority = PRIORITY_MEDIUM
        for raw in plan.get("actions", []):
            if raw.get("id") == action_id:
                priority = raw.get("priority", PRIORITY_MEDIUM)
                break

        score = await self.score_service.record_action_completion(
            user_id, farm_id, action_id, plan_id, priority
        )
        return CopilotActionCompleteResponse(
            action_id=action_id,
            completed=True,
            yield_protection_score=score.score,
        )

    async def _completed_action_ids(self, user_id: str, farm_id: str) -> set[str]:
        cursor = self.db.copilot_action_completions.find(
            {"user_id": ObjectId(user_id), "farm_id": ObjectId(farm_id)}
        )
        return {doc["action_id"] async for doc in cursor}

    def _build_explain_context(
        self, core, severity, advisory: AdvisoryActionsResponse, field_context
    ) -> dict[str, Any]:
        latest_status = "HEALTHY"
        disease_name = "Disease"
        return {
            "fsi_pct": int(core.fsi * 100),
            "primary_factor": core.primary_factor,
            "crop": core.crop_type,
            "stage": core.stage,
            "humidity": int(field_context.weather.current.humidity),
            "disease_name": disease_name,
            "severity_tier": severity.severity_tier,
        }

    def _card_to_copilot_action(
        self,
        card: ActionCard,
        horizon: str,
        plan_priority: str,
        ctx: dict[str, Any],
        completed_ids: set[str],
    ) -> CopilotAction:
        action_id = self._stable_action_id(card, horizon)
        priority = self._card_priority(card, plan_priority)
        why, if_ignored, benefit = self._explain_for_card(card, ctx)

        return CopilotAction(
            id=action_id,
            horizon=horizon,
            priority=priority,
            card_type=card.card_type,
            title=card.problem,
            action=card.action,
            deadline=card.deadline,
            expected_impact=card.expected_impact,
            why=why,
            if_ignored=if_ignored,
            expected_benefit=benefit,
            source_signals=[],
            is_sos=bool(card.is_sos),
            completed=action_id in completed_ids,
        )

    def _explain_for_card(
        self, card: ActionCard, ctx: dict[str, Any]
    ) -> tuple[str, str, str]:
        problem_lower = card.problem.lower()
        if card.is_sos:
            tpl = EXPLAIN_AUTO_SOS
        elif "rust" in problem_lower or "disease" in problem_lower or "infection" in problem_lower:
            tpl = EXPLAIN_DISEASE_CONFIRMED
        elif "stress" in problem_lower and "high" in problem_lower:
            tpl = EXPLAIN_FSI_HIGH
        elif "stress" in problem_lower or "fsi" in problem_lower:
            tpl = EXPLAIN_FSI_MEDIUM
        elif "rainfall" in problem_lower or "deficit" in problem_lower:
            tpl = EXPLAIN_RAINFALL_DEFICIT
        elif "temperature" in problem_lower or "thermal" in problem_lower:
            tpl = EXPLAIN_THERMAL_HIGH
        elif "humidity" in problem_lower:
            tpl = EXPLAIN_HUMIDITY_RUST
        elif card.card_type == CARD_GREEN:
            tpl = EXPLAIN_ROUTINE_HEALTHY if "routine" in problem_lower else EXPLAIN_PREVENTIVE_SCOUTING
        else:
            return card.problem, DEFAULT_IF_IGNORED, DEFAULT_EXPECTED_BENEFIT

        try:
            return tpl[0].format(**ctx), tpl[1], tpl[2]
        except KeyError:
            return tpl[0], tpl[1], tpl[2]

    def _preventive_actions(
        self, core, field_context, ctx: dict[str, Any], completed_ids: set[str]
    ) -> list[CopilotAction]:
        actions: list[CopilotAction] = []
        humidity = field_context.weather.current.humidity
        if (
            humidity > 80.0
            and core.crop_type.upper() == "WHEAT"
            and core.fsi < 0.65
            and not core.disease_present
        ):
            why, if_ignored, benefit = EXPLAIN_HUMIDITY_RUST[0].format(**ctx), EXPLAIN_HUMIDITY_RUST[1], EXPLAIN_HUMIDITY_RUST[2]
            card = ActionCard(
                card_type=CARD_YELLOW,
                problem=f"High humidity ({int(humidity)}%) — rust scouting recommended",
                action="Inspect lower leaves for rust pustules during morning hours",
                deadline="This week",
                expected_impact="Early detection supports potential loss prevention",
            )
            actions.append(
                self._card_to_copilot_action(
                    card, HORIZON_PREVENTIVE, PRIORITY_MEDIUM, ctx, completed_ids
                )
            )

        if core.fsi < 0.35 and not core.disease_present:
            why, if_ignored, benefit = (
                EXPLAIN_PREVENTIVE_SCOUTING[0].format(**ctx),
                EXPLAIN_PREVENTIVE_SCOUTING[1],
                EXPLAIN_PREVENTIVE_SCOUTING[2],
            )
            card = ActionCard(
                card_type=CARD_GREEN,
                problem=f"Routine scouting at {core.stage} stage",
                action="Walk field perimeter and check for early stress or pest signs",
                deadline="This week",
                expected_impact="Maintains readiness for early intervention",
            )
            actions.append(
                self._card_to_copilot_action(
                    card, HORIZON_PREVENTIVE, PRIORITY_LOW, ctx, completed_ids
                )
            )
        return actions

    @staticmethod
    def _stable_action_id(card: ActionCard, horizon: str) -> str:
        key = f"{horizon}:{card.problem}:{card.action}"
        return hashlib.sha256(key.encode()).hexdigest()[:16]

    @staticmethod
    def _card_priority(card: ActionCard, plan_priority: str) -> str:
        if card.is_sos:
            return PRIORITY_EMERGENCY
        if card.card_type == CARD_RED:
            return PRIORITY_HIGH
        if card.card_type == CARD_YELLOW:
            return PRIORITY_MEDIUM
        return PRIORITY_LOW if plan_priority == PRIORITY_LOW else plan_priority

    @staticmethod
    def _resolve_priority(advisory_priority: str, severity_tier: str) -> str:
        advisory_rank = PRIORITY_RANK.get(advisory_priority, 1)
        severity_rank = SEVERITY_RANK.get(severity_tier, 1)
        if severity_rank >= 4:
            return PRIORITY_EMERGENCY
        if advisory_rank >= 4:
            return PRIORITY_EMERGENCY
        if severity_rank >= 3 or advisory_rank >= 3:
            return PRIORITY_HIGH
        if severity_rank >= 2 or advisory_rank >= 2:
            return PRIORITY_MEDIUM
        return PRIORITY_LOW
