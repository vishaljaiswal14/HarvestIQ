from typing import Annotated

from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.database import get_database
from app.models.day5_schemas import LocalizationResponse
from app.services.localization_service import LocalizationService

router = APIRouter(prefix="/localization", tags=["localization"])


@router.get("/{lang}", response_model=LocalizationResponse)
async def get_localization(
    lang: str,
    db: Annotated[AsyncIOMotorDatabase, Depends(get_database)],
) -> LocalizationResponse:
    service = LocalizationService(db)
    return await service.get_labels(lang)
