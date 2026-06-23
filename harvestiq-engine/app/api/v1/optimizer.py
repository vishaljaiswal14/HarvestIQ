from typing import Annotated

from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.api.deps import get_current_user
from app.core.database import get_database
from app.models.day6_schemas import InputWindowRequest, InputWindowResponse
from app.services.input_window_optimizer_service import InputWindowOptimizerService

router = APIRouter(prefix="/optimizer", tags=["optimizer"])


@router.post("/window", response_model=InputWindowResponse)
async def evaluate_input_window(
    payload: InputWindowRequest,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncIOMotorDatabase, Depends(get_database)],
) -> InputWindowResponse:
    service = InputWindowOptimizerService(db)
    return await service.evaluate(str(current_user["_id"]), payload.farm_id, payload.action_type)
