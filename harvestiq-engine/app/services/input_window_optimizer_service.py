from datetime import datetime, timezone

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.config import get_settings
from app.core.constants.optimizer import ACTION_FERTILIZE, ACTION_IRRIGATE, ACTION_SPRAY, ALLOWED_ACTIONS
from app.core.exceptions import unprocessable_entity
from app.models.day6_schemas import InputWindowResponse
from app.models.engine_schemas import ExplanationPayload
from app.services.deterministic_engine import evaluate_input_window
from app.services.explainability_service import build_optimizer_explanation
from app.services.stress_index_service import StressIndexService


class InputWindowOptimizerService:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self.db = db
        self.stress_service = StressIndexService(db)
        self.settings = get_settings()

    async def evaluate(self, user_id: str, farm_id: str, action_type: str) -> InputWindowResponse:
        action = action_type.strip().upper()
        if action not in ALLOWED_ACTIONS:
            raise unprocessable_entity(f"Unsupported action type: {action_type}")

        fsi_result = await self.stress_service.compute(farm_id, user_id)
        context = await self.stress_service.build_field_context(farm_id, user_id)
        weather = context.weather
        forecast_rain = sum(day.precipitation for day in weather.forecast[:3])

        safe, reasons, rules = evaluate_input_window(
            wind_speed_kmh=weather.current.wind_speed,
            forecast_rain_mm_3d=forecast_rain,
            fsi_classification=fsi_result.classification,
            action_type=action,
            wind_limit=self.settings.optimizer_wind_limit_kmh,
            rain_limit=self.settings.optimizer_rain_limit_mm,
        )

        explanation_dict = build_optimizer_explanation(
            action_type=action,
            safe=safe,
            reasons=reasons,
            triggered_rules=rules,
            inputs={
                "wind_speed": weather.current.wind_speed,
                "forecast_rain_3d": forecast_rain,
                "fsi_classification": fsi_result.classification,
            },
        )

        now = datetime.now(timezone.utc)
        return InputWindowResponse(
            farm_id=farm_id,
            action_type=action,
            safe=safe,
            reasons=reasons,
            triggered_rules=rules,
            explanation=ExplanationPayload(**explanation_dict),
            evaluated_at=now,
            cycle_status=context.cycle_status,
        )

    async def evaluate_all(self, user_id: str, farm_id: str) -> dict[str, bool]:
        results: dict[str, bool] = {}
        for action in (ACTION_SPRAY, ACTION_IRRIGATE, ACTION_FERTILIZE):
            response = await self.evaluate(user_id, farm_id, action)
            results[action] = response.safe
        return results
