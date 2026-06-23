from datetime import datetime, timezone

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.constants.crop_stages import CropCycleStatus
from app.core.constants.crop_types import normalize_crop_type
from app.core.exceptions import unprocessable_entity
from app.models.day6_schemas import MarketPriceRecord, MarketPricesResponse
from app.services.farm_access_service import get_owned_farm


class MarketIntelligenceService:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self.db = db

    async def get_prices(self, user_id: str, farm_id: str) -> MarketPricesResponse:
        farm = await get_owned_farm(self.db, farm_id, user_id)
        state = str(farm.get("state", "")).upper()

        from app.services.farm_access_service import get_latest_relevant_crop_cycle
        cycle, cycle_status = await get_latest_relevant_crop_cycle(self.db, farm_id)
        crop_type = normalize_crop_type(cycle["crop_type"])

        cursor = self.db.market_prices.find(
            {"crop_type": crop_type, "state": state},
        ).sort("price_date", -1).limit(7)

        prices: list[MarketPriceRecord] = []
        async for doc in cursor:
            prices.append(
                MarketPriceRecord(
                    mandi=doc["mandi"],
                    crop_type=doc["crop_type"],
                    min_price=float(doc["min_price"]),
                    max_price=float(doc["max_price"]),
                    modal_price=float(doc["modal_price"]),
                    price_date=doc["price_date"],
                )
            )

        modal_trend = "STABLE"
        if len(prices) >= 2:
            if prices[0].modal_price > prices[1].modal_price:
                modal_trend = "RISING"
            elif prices[0].modal_price < prices[1].modal_price:
                modal_trend = "FALLING"

        return MarketPricesResponse(
            farm_id=farm_id,
            crop_type=crop_type,
            prices=prices,
            modal_trend=modal_trend,
            as_of=datetime.now(timezone.utc),
            cycle_status=cycle_status,
        )

    async def get_summary_for_farm(self, user_id: str, farm_id: str) -> dict | None:
        try:
            response = await self.get_prices(user_id, farm_id)
        except Exception:
            return None
        if not response.prices:
            return None
        latest = response.prices[0]
        return {
            "mandi": latest.mandi,
            "modal_price": latest.modal_price,
            "trend": response.modal_trend,
            "crop_type": response.crop_type,
        }
