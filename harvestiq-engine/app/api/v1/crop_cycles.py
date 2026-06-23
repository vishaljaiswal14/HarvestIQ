from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.core.database import get_database
from app.models.engine_schemas import (
    CropCycleCreateResponse,
    CropCycleCreateSchema,
    CropStageResponse,
)
from app.services.crop_stage_service import CropStageService

router = APIRouter(prefix="/crop-cycles", tags=["crop-cycles"])


@router.post("", response_model=CropCycleCreateResponse, status_code=201)
async def create_crop_cycle(
    payload: CropCycleCreateSchema,
    current_user: Annotated[dict, Depends(get_current_user)],
) -> CropCycleCreateResponse:
    db = get_database()
    service = CropStageService(db)
    return await service.create_crop_cycle(str(current_user["_id"]), payload)


@router.get("/{cycle_id}/stage", response_model=CropStageResponse)
async def get_crop_stage(
    cycle_id: str,
    current_user: Annotated[dict, Depends(get_current_user)],
) -> CropStageResponse:
    db = get_database()
    service = CropStageService(db)
    return await service.get_crop_stage(cycle_id, str(current_user["_id"]))
