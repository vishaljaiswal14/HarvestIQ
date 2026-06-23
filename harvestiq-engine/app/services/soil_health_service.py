import json
from datetime import datetime, timezone
from pathlib import Path

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.constants.crop_stages import CropCycleStatus
from app.core.constants.soil import NUTRIENT_KEYS
from app.core.constants.crop_types import normalize_crop_type
from app.core.exceptions import unprocessable_entity
from app.models.day4_schemas import NutrientDeficiencyStatus, SoilRecordCreateSchema, SoilRecordResponse
from app.services.deterministic_engine import compute_soil_health_index
from app.services.explainability_service import build_soil_explanation
from app.services.farm_access_service import get_owned_farm


class SoilHealthService:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self.db = db
        self.reference_ranges = self._load_reference_ranges()

    async def create_record(self, user_id: str, payload: SoilRecordCreateSchema, language: str = "en") -> SoilRecordResponse:
        farm = await get_owned_farm(self.db, payload.farm_id, user_id)
        crop_type = await self._resolve_crop_type(payload.farm_id)

        ranges = self.reference_ranges.get(crop_type)
        if ranges is None:
            raise unprocessable_entity(f"No soil reference ranges for crop type: {crop_type}")

        measurements = {
            "nitrogen": payload.nitrogen,
            "phosphorus": payload.phosphorus,
            "potassium": payload.potassium,
            "ph": payload.ph,
            "organic_carbon": payload.organic_carbon,
            "electrical_conductivity": payload.electrical_conductivity,
        }
        soil_health_index, deficiency_status, nutrient_scores = compute_soil_health_index(
            measurements,
            ranges,
        )
        primary_factor = self._resolve_primary_factor(deficiency_status, nutrient_scores)
        recorded_at = payload.recorded_at or datetime.now(timezone.utc)

        inputs = {
            **measurements,
            "crop_type": crop_type,
            "state": farm.get("state"),
            "district": farm.get("district"),
            "nutrient_scores": nutrient_scores,
        }
        explanation = build_soil_explanation(
            soil_health_index,
            primary_factor,
            inputs,
            deficiency_status,
            language=language,
        )

        doc = {
            "user_id": ObjectId(user_id),
            "farm_id": ObjectId(payload.farm_id),
            "crop_type": crop_type,
            **measurements,
            "deficiency_status": deficiency_status,
            "soil_health_index": soil_health_index,
            "explanation": explanation,
            "recorded_at": recorded_at,
            "created_at": datetime.now(timezone.utc),
        }
        result = await self.db.soil_records.insert_one(doc)
        doc["_id"] = result.inserted_id
        return self._to_response(doc)

    async def get_latest(self, user_id: str, farm_id: str, language: str = "en") -> SoilRecordResponse | dict:
        await get_owned_farm(self.db, farm_id, user_id)
        doc = await self.db.soil_records.find_one(
            {"farm_id": ObjectId(farm_id)},
            sort=[("recorded_at", -1)],
        )
        if doc is None:
            return {"available": False, "message": "No soil record submitted yet"}
        
        # Re-build explanation dynamically based on user language preference
        measurements = {
            "nitrogen": doc["nitrogen"],
            "phosphorus": doc["phosphorus"],
            "potassium": doc["potassium"],
            "ph": doc["ph"],
            "organic_carbon": doc["organic_carbon"],
            "electrical_conductivity": doc["electrical_conductivity"],
        }
        ranges = self.reference_ranges.get(doc["crop_type"])
        if ranges:
            _, deficiency_status, nutrient_scores = compute_soil_health_index(measurements, ranges)
            primary_factor = self._resolve_primary_factor(deficiency_status, nutrient_scores)
            inputs = {
                **measurements,
                "crop_type": doc["crop_type"],
                "nutrient_scores": nutrient_scores,
            }
            doc["explanation"] = build_soil_explanation(
                doc["soil_health_index"],
                primary_factor,
                inputs,
                deficiency_status,
                language=language
            )

        return self._to_response(doc)

    async def _resolve_crop_type(self, farm_id: str) -> str:
        from app.services.farm_access_service import get_latest_relevant_crop_cycle
        cycle, cycle_status = await get_latest_relevant_crop_cycle(self.db, farm_id)
        return normalize_crop_type(cycle["crop_type"])

    @staticmethod
    def _resolve_primary_factor(
        deficiency_status: dict[str, str],
        nutrient_scores: dict[str, float],
    ) -> str:
        low_items = [key for key, status in deficiency_status.items() if status == "LOW"]
        if low_items:
            return low_items[0].upper()
        worst = min(nutrient_scores.items(), key=lambda item: item[1])[0]
        return worst.upper()

    @staticmethod
    def _load_reference_ranges() -> dict:
        path = Path(__file__).resolve().parents[2] / "data" / "soil_reference_ranges.json"
        with path.open(encoding="utf-8") as handle:
            return json.load(handle)

    @staticmethod
    def _to_response(doc: dict) -> SoilRecordResponse:
        recorded_at = doc["recorded_at"]
        if isinstance(recorded_at, datetime) and recorded_at.tzinfo is None:
            recorded_at = recorded_at.replace(tzinfo=timezone.utc)

        status = doc["deficiency_status"]
        return SoilRecordResponse(
            id=str(doc["_id"]),
            farm_id=str(doc["farm_id"]),
            crop_type=doc["crop_type"],
            nitrogen=doc["nitrogen"],
            phosphorus=doc["phosphorus"],
            potassium=doc["potassium"],
            ph=doc["ph"],
            organic_carbon=doc["organic_carbon"],
            electrical_conductivity=doc["electrical_conductivity"],
            deficiency_status=NutrientDeficiencyStatus(**{key: status[key] for key in NUTRIENT_KEYS}),
            soil_health_index=doc["soil_health_index"],
            explanation=doc["explanation"],
            recorded_at=recorded_at,
        )
