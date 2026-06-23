from datetime import datetime, timezone

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.constants.crop_types import normalize_crop_type
from app.core.exceptions import conflict, not_found
from app.services.location_service import build_farm_location
from app.models.farm_models import (
    FarmProfileResponse,
    OnboardingResponse,
    OnboardingSchema,
)


class OnboardingService:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self.db = db

    async def complete_onboarding(
        self,
        user_id: str,
        payload: OnboardingSchema,
    ) -> OnboardingResponse:
        user = await self.db.users.find_one({"_id": ObjectId(user_id)})
        if user is None:
            raise not_found("User not found")

        if user.get("onboarding_completed"):
            raise conflict("User has already completed onboarding")

        existing_farm = await self.db.farms.find_one({"user_id": ObjectId(user_id)})
        if existing_farm is not None:
            raise conflict("Farm profile already exists for this user")

        now = datetime.now(timezone.utc)
        farm_name = payload.farm_name or f"{user['name']}'s Farm"

        location_fields = build_farm_location(payload.state, payload.district)
        farm_doc = {
            "user_id": ObjectId(user_id),
            "name": farm_name,
            "state": payload.state,
            "district": payload.district,
            "boundary": payload.boundary.model_dump() if payload.boundary else None,
            "soil_type": payload.soil_type,
            "created_at": now,
            **location_fields,
        }
        farm_result = await self.db.farms.insert_one(farm_doc)
        farm_id = farm_result.inserted_id

        sowing_datetime = datetime.combine(
            payload.sowing_date,
            datetime.min.time(),
            tzinfo=timezone.utc,
        )
        crop_doc = {
            "farm_id": farm_id,
            "crop_type": normalize_crop_type(payload.crop_type),
            "sowing_date": sowing_datetime,
            "current_gdd": 0.0,
            "status": "ACTIVE",
            "updated_at": now,
        }
        crop_result = await self.db.crop_cycles.insert_one(crop_doc)

        await self.db.users.update_one(
            {"_id": ObjectId(user_id)},
            {
                "$set": {
                    "onboarding_completed": True,
                    "updated_at": now,
                }
            },
        )

        return OnboardingResponse(
            farm_id=str(farm_id),
            crop_cycle_id=str(crop_result.inserted_id),
        )

    async def get_farm_profile(self, user_id: str, language: str = "en") -> FarmProfileResponse:
        farm = await self.db.farms.find_one({"user_id": ObjectId(user_id)})
        if farm is None:
            raise not_found("Farm profile not found")

        # Resolve all plots belonging to the farm
        plots_cursor = self.db.plots.find({"farm_id": farm["_id"]}, {"_id": 1})
        plot_ids = [p["_id"] async for p in plots_cursor]

        crop_cycle = await self.db.crop_cycles.find_one(
            {
                "status": "ACTIVE",
                "$or": [
                    {"farm_id": farm["_id"]},
                    {"plot_id": {"$in": plot_ids}}
                ]
            },
            sort=[("updated_at", -1)],
        )

        sowing_date = None
        if crop_cycle and crop_cycle.get("sowing_date"):
            sowing_date = crop_cycle["sowing_date"].date()

        soil_type = farm.get("soil_type")
        crop_type = crop_cycle.get("crop_type") if crop_cycle else None

        lang_str = str(language).strip().lower()
        if lang_str == "hi":
            CROP_MAP = {"WHEAT": "गेहूं", "PADDY": "धान", "MAIZE": "मक्का"}
            SOIL_MAP = {"CLAY": "चिकनी मिट्टी (Clay)", "LOAM": "दुमट मिट्टी (Loam)"}
            if soil_type:
                soil_type = SOIL_MAP.get(soil_type, soil_type)
            if crop_type:
                crop_type = CROP_MAP.get(crop_type, crop_type)

        return FarmProfileResponse(
            farm_id=str(farm["_id"]),
            farm_name=farm["name"],
            state=farm["state"],
            district=farm["district"],
            soil_type=soil_type,
            boundary=farm.get("boundary"),
            crop_cycle_id=str(crop_cycle["_id"]) if crop_cycle else None,
            crop_type=crop_type,
            sowing_date=sowing_date,
        )
