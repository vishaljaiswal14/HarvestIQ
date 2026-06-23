from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.api.deps import get_current_user
from app.core.database import get_database
from app.models.day6_schemas import HealthCardResponse
from app.services.health_card_service import HealthCardService

router = APIRouter(prefix="/health-card", tags=["health-card"])


@router.get("", response_model=HealthCardResponse)
async def get_health_card(
    farm_id: Annotated[str, Query()],
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncIOMotorDatabase, Depends(get_database)],
    request: Request,
) -> HealthCardResponse:
    service = HealthCardService(db)
    accept_lang = request.headers.get("accept-language")
    if accept_lang:
        language = accept_lang.split(",")[0].split(";")[0].strip().lower()
    else:
        language = current_user.get("preferred_lang", "en")
    if language not in ["hi", "en", "mr"]:
        language = "hi"
    return await service.get_health_card(str(current_user["_id"]), farm_id, language=language)
