from dataclasses import dataclass
from datetime import datetime, timezone

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.constants.crop_stages import CropCycleStatus
from app.core.constants.fsi import (
    DEFAULT_STAGE_VULNERABILITY,
    EXPECTED_DAILY_RAINFALL_MM,
    RAINFALL_WINDOW_DAYS,
    STRESS_LOG_FSI_DELTA_THRESHOLD,
)
from app.core.constants.crop_types import normalize_crop_type
from app.core.exceptions import unprocessable_entity
from app.models.engine_schemas import (
    CropCharacteristicsInDB,
    CropStageDefinition,
    FsiComponents,
    StressIndexResponse,
    WeatherForecastResponse,
)
from app.services.deterministic_engine import (
    accumulate_gdd,
    calculate_gdd_scale,
    calculate_rainfall_deficit,
    calculate_temp_stress,
    classify_fsi,
    compute_fsi,
    resolve_growth_stage,
    resolve_primary_factor,
)
from app.services.explainability_service import build_fsi_explanation
from app.services.farm_access_service import get_owned_farm
from app.services.weather_service import WeatherService


@dataclass
class FieldContext:
    farm: dict
    cycle: dict
    characteristics: CropCharacteristicsInDB
    weather: WeatherForecastResponse
    stage_name: str
    current_gdd: float
    current_stage_def: CropStageDefinition
    cycle_status: str = "ACTIVE"



class StressIndexService:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self.db = db
        self.weather_service = WeatherService(db)

    async def compute(self, farm_id: str, user_id: str, language: str = "en") -> StressIndexResponse:
        context = await self._build_field_context(farm_id, user_id)
        result = self._calculate_fsi(context, language)
        await self._maybe_persist_stress_log(farm_id, user_id, context, result)
        return result

    async def build_field_context(self, farm_id: str, user_id: str) -> FieldContext:
        return await self._build_field_context(farm_id, user_id)

    def calculate_fsi_from_context(self, context: FieldContext, language: str = "en") -> StressIndexResponse:
        return self._calculate_fsi(context, language)

    async def _build_field_context(self, farm_id: str, user_id: str) -> FieldContext:
        farm = await get_owned_farm(self.db, farm_id, user_id)

        from app.services.farm_access_service import get_latest_relevant_crop_cycle
        cycle, cycle_status = await get_latest_relevant_crop_cycle(self.db, farm_id)

        crop_type = normalize_crop_type(cycle["crop_type"])
        characteristics = await self._get_characteristics(crop_type)
        base_temp = float(characteristics.gdd_base_temp)

        weather = await self.weather_service.get_forecast(
            farm_id,
            user_id,
            gdd_base_temp=base_temp,
        )

        sowing_date = cycle["sowing_date"].date()
        daily_pairs = [(entry.date, entry.gdd) for entry in weather.daily_gdd]
        current_gdd = accumulate_gdd(daily_pairs, sowing_date)

        stage_name, _, _ = resolve_growth_stage(current_gdd, characteristics.stages)
        current_stage_def = self._resolve_stage_def(stage_name, characteristics.stages)

        return FieldContext(
            farm=farm,
            cycle=cycle,
            characteristics=characteristics,
            weather=weather,
            stage_name=stage_name,
            current_gdd=current_gdd,
            current_stage_def=current_stage_def,
            cycle_status=cycle_status,
        )

    def _calculate_fsi(self, context: FieldContext, language: str = "en") -> StressIndexResponse:
        forecast_temp_max = [day.temp_max for day in context.weather.forecast]
        forecast_precip = [day.precipitation for day in context.weather.forecast]

        temp_stress = calculate_temp_stress(context.weather.current.temp, forecast_temp_max)
        rainfall_deficit = calculate_rainfall_deficit(
            forecast_precip,
            expected_daily_mm=EXPECTED_DAILY_RAINFALL_MM,
            days=RAINFALL_WINDOW_DAYS,
        )
        stage_vuln = context.characteristics.stage_vulnerability.get(
            context.stage_name,
            DEFAULT_STAGE_VULNERABILITY,
        )
        gdd_scale = calculate_gdd_scale(
            context.current_gdd,
            context.current_stage_def.gdd_max,
            stage_vuln,
        )

        fsi = compute_fsi(temp_stress, rainfall_deficit, gdd_scale)
        classification = classify_fsi(fsi)
        primary_factor = resolve_primary_factor(temp_stress, rainfall_deficit, gdd_scale)

        inputs = {
            "current_temp": round(context.weather.current.temp, 2),
            "forecast_temp_max_3d": round(
                max(forecast_temp_max[:3]) if forecast_temp_max else context.weather.current.temp,
                2,
            ),
            "rainfall_3d_mm": round(sum(forecast_precip[:RAINFALL_WINDOW_DAYS]), 2),
            "rainfall_deficit": rainfall_deficit,
            "current_gdd": context.current_gdd,
            "stage": context.stage_name,
            "stage_vulnerability": stage_vuln,
            "temp_stress": temp_stress,
            "gdd_scale": gdd_scale,
        }

        explanation = build_fsi_explanation(fsi, classification, primary_factor, inputs, language)
        now = datetime.now(timezone.utc)

        return StressIndexResponse(
            farm_id=str(context.farm["_id"]),
            crop_cycle_id=str(context.cycle["_id"]),
            crop_type=normalize_crop_type(context.cycle["crop_type"]),
            stage=context.stage_name,
            fsi=fsi,
            classification=classification,
            primary_factor=primary_factor,
            components=FsiComponents(
                temp_stress=temp_stress,
                rainfall_deficit=rainfall_deficit,
                gdd_scale=gdd_scale,
            ),
            calculated_at=now,
            explanation=explanation,
            cycle_status=context.cycle_status,
        )

    async def _maybe_persist_stress_log(
        self,
        farm_id: str,
        user_id: str,
        context: FieldContext,
        result: StressIndexResponse,
    ) -> None:
        latest = await self.db.stress_logs.find_one(
            {"farm_id": ObjectId(farm_id)},
            sort=[("calculated_at", -1)],
        )

        if latest is not None:
            same_classification = latest.get("classification") == result.classification
            fsi_delta = abs(float(latest.get("fsi_score", 0.0)) - result.fsi)
            if same_classification and fsi_delta < STRESS_LOG_FSI_DELTA_THRESHOLD:
                return

        await self.db.stress_logs.insert_one(
            {
                "farm_id": ObjectId(farm_id),
                "user_id": ObjectId(user_id),
                "crop_cycle_id": ObjectId(str(context.cycle["_id"])),
                "crop_type": result.crop_type,
                "stage": result.stage,
                "fsi_score": result.fsi,
                "classification": result.classification,
                "primary_factor": result.primary_factor,
                "components": result.components.model_dump(),
                "explanation": result.explanation.model_dump(),
                "calculated_at": result.calculated_at,
            }
        )

    async def _get_characteristics(self, crop_type: str) -> CropCharacteristicsInDB:
        doc = await self.db.crop_characteristics.find_one({"crop_type": crop_type})
        if doc is None:
            raise unprocessable_entity(f"Unsupported crop type: {crop_type}")
        return CropCharacteristicsInDB(**doc)

    @staticmethod
    def _resolve_stage_def(
        stage_name: str,
        stages: list[CropStageDefinition],
    ) -> CropStageDefinition:
        for stage in stages:
            if stage.name == stage_name:
                return stage
        return stages[-1] if stages else CropStageDefinition(name="Unknown", gdd_min=0, gdd_max=1)
