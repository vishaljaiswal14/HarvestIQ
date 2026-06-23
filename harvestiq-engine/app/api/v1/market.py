from typing import Annotated

from fastapi import APIRouter, Depends, Query
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.api.deps import get_current_user
from app.core.database import get_database
from app.models.day6_schemas import MarketPricesResponse
from app.services.market_intelligence_service import MarketIntelligenceService

router = APIRouter(prefix="/market", tags=["market"])


@router.get("/prices", response_model=MarketPricesResponse)
async def get_market_prices(
    farm_id: Annotated[str, Query()],
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncIOMotorDatabase, Depends(get_database)],
) -> MarketPricesResponse:
    service = MarketIntelligenceService(db)
    return await service.get_prices(str(current_user["_id"]), farm_id)
