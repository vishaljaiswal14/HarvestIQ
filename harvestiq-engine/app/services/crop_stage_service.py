from datetime import datetime, timezone

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.constants.crop_stages import CropCycleStatus
from app.core.constants.crop_types import normalize_crop_type
from app.core.exceptions import unprocessable_entity
from app.models.engine_schemas import (
    CropCharacteristicsInDB,
    CropCycleCreateResponse,
    CropCycleCreateSchema,
    CropStageDefinition,
    CropStageResponse,
)
from app.services.deterministic_engine import accumulate_gdd, resolve_growth_stage
from app.services.farm_access_service import get_owned_crop_cycle, get_owned_farm
from app.services.weather_service import WeatherService


class CropStageService:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self.db = db
        self.weather_service = WeatherService(db)

    async def create_crop_cycle(
        self,
        user_id: str,
        payload: CropCycleCreateSchema,
    ) -> CropCycleCreateResponse:
        await get_owned_farm(self.db, payload.farm_id, user_id)
        crop_type = normalize_crop_type(payload.crop_type)
        await self._get_characteristics(crop_type)

        await self.db.crop_cycles.update_many(
            {"farm_id": ObjectId(payload.farm_id), "status": CropCycleStatus.ACTIVE.value},
            {"$set": {"status": CropCycleStatus.HARVESTED.value, "updated_at": datetime.now(timezone.utc)}},
        )

        now = datetime.now(timezone.utc)
        sowing_datetime = datetime.combine(
            payload.sowing_date,
            datetime.min.time(),
            tzinfo=timezone.utc,
        )
        result = await self.db.crop_cycles.insert_one(
            {
                "farm_id": ObjectId(payload.farm_id),
                "crop_type": crop_type,
                "sowing_date": sowing_datetime,
                "current_gdd": 0.0,
                "status": CropCycleStatus.ACTIVE.value,
                "updated_at": now,
            }
        )

        return CropCycleCreateResponse(id=str(result.inserted_id))

    async def get_crop_stage(self, cycle_id: str, user_id: str) -> CropStageResponse:
        cycle, farm = await get_owned_crop_cycle(self.db, cycle_id, user_id)
        crop_type = normalize_crop_type(cycle["crop_type"])
        characteristics = await self._get_characteristics(crop_type)

        base_temp = float(characteristics.gdd_base_temp)
        forecast = await self.weather_service.get_forecast(
            str(farm["_id"]),
            user_id,
            gdd_base_temp=base_temp,
        )

        sowing_date = cycle["sowing_date"].date()
        daily_pairs = [(entry.date, entry.gdd) for entry in forecast.daily_gdd]
        accumulated = accumulate_gdd(daily_pairs, sowing_date)

        now = datetime.now(timezone.utc)
        await self.db.crop_cycles.update_one(
            {"_id": cycle["_id"]},
            {"$set": {"current_gdd": accumulated, "updated_at": now}},
        )

        stage_defs = characteristics.stages
        stage_name, progress, timeline = resolve_growth_stage(accumulated, stage_defs)

        return CropStageResponse(
            cycle_id=cycle_id,
            crop_type=crop_type,
            stage=stage_name,
            progress_percentage=progress,
            current_gdd=accumulated,
            stages_timeline=timeline,
        )

    async def _get_characteristics(self, crop_type: str) -> CropCharacteristicsInDB:
        doc = await self.db.crop_characteristics.find_one({"crop_type": crop_type})
        if doc is None:
            raise unprocessable_entity(f"Unsupported crop type: {crop_type}")
        return CropCharacteristicsInDB(**doc)
