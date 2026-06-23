from datetime import datetime, timezone

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.models.day6_schemas import SchemeMatch, SchemesEligibleResponse
from app.services.farm_access_service import get_owned_farm


class SchemeEligibilityService:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self.db = db

    async def get_eligible(self, user_id: str, farm_id: str) -> SchemesEligibleResponse:
        farm = await get_owned_farm(self.db, farm_id, user_id)
        state = str(farm.get("state", "")).upper()
        crop_type = ""
        from app.services.farm_access_service import get_latest_relevant_crop_cycle
        try:
            cycle, cycle_status = await get_latest_relevant_crop_cycle(self.db, farm_id)
        except Exception:
            cycle = None
        if cycle:
            crop_type = str(cycle.get("crop_type", "")).upper()

        cursor = self.db.schemes.find({"active": True})
        matches: list[SchemeMatch] = []
        async for scheme in cursor:
            if not self._is_eligible(scheme, state, crop_type):
                continue
            matches.append(
                SchemeMatch(
                    scheme_id=str(scheme.get("scheme_id", scheme["_id"])),
                    name=scheme["name"],
                    description=scheme.get("description", ""),
                    application_steps=list(scheme.get("application_steps", [])),
                )
            )

        return SchemesEligibleResponse(
            farm_id=farm_id,
            schemes=matches,
            evaluated_at=datetime.now(timezone.utc),
        )

    @staticmethod
    def _is_eligible(scheme: dict, state: str, crop_type: str) -> bool:
        eligible_states = [s.upper() for s in scheme.get("eligible_states", ["ALL"])]
        if "ALL" not in eligible_states and state not in eligible_states:
            return False
        eligible_crops = [c.upper() for c in scheme.get("eligible_crops", ["ALL"])]
        if crop_type and "ALL" not in eligible_crops and crop_type not in eligible_crops:
            return False
        return True
