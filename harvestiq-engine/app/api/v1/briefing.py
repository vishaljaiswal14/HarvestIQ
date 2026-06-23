from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query, Request
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.api.deps import get_current_user
from app.core.database import get_database
from app.models.day6_schemas import BriefingResponse
from app.services.briefing_service import BriefingService

router = APIRouter(prefix="/briefing", tags=["briefing"])


@router.get("/daily", response_model=BriefingResponse)
async def get_daily_briefing(
    farm_id: str,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncIOMotorDatabase, Depends(get_database)],
    request: Request,
    language: Optional[str] = Query(default=None),
    force_regenerate: bool = Query(default=False),
) -> BriefingResponse:
    if not language:
        accept_lang = request.headers.get("accept-language", "hi")
        language = accept_lang.split(",")[0].split(";")[0].strip().lower()
    if language not in ["hi", "en", "mr"]:
        language = "hi"

    service = BriefingService(db)
    return await service.get_daily_briefing(
        str(current_user["_id"]),
        farm_id,
        language=language,
        force_regenerate=force_regenerate,
    )

