from typing import Annotated, Union

from fastapi import APIRouter, Depends, Query
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.api.deps import get_current_user
from app.core.database import get_database
from app.models.day4_schemas import SoilRecordCreateSchema, SoilRecordResponse, SoilRecordUnavailableResponse
from app.services.soil_health_service import SoilHealthService

router = APIRouter(prefix="/soil", tags=["soil"])


@router.post("/records", response_model=SoilRecordResponse, status_code=201)
async def create_soil_record(
    payload: SoilRecordCreateSchema,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncIOMotorDatabase, Depends(get_database)],
) -> SoilRecordResponse:
    service = SoilHealthService(db)
    lang = current_user.get("preferred_lang", "hi")
    return await service.create_record(str(current_user["_id"]), payload, language=lang)


@router.get("/records/latest", response_model=Union[SoilRecordResponse, SoilRecordUnavailableResponse])
async def get_latest_soil_record(
    farm_id: Annotated[str, Query(...)],
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncIOMotorDatabase, Depends(get_database)],
) -> Union[SoilRecordResponse, SoilRecordUnavailableResponse]:
    service = SoilHealthService(db)
    lang = current_user.get("preferred_lang", "hi")
    return await service.get_latest(str(current_user["_id"]), farm_id, language=lang)
