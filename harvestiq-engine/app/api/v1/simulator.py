from typing import Annotated

from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.api.deps import get_current_user
from app.core.database import get_database
from app.models.day6_schemas import SimulatorRequest, SimulatorResponse
from app.services.simulator_service import SimulatorService

router = APIRouter(prefix="/simulator", tags=["simulator"])


@router.post("/run", response_model=SimulatorResponse)
async def run_simulator(
    payload: SimulatorRequest,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncIOMotorDatabase, Depends(get_database)],
) -> SimulatorResponse:
    service = SimulatorService(db)
    return await service.run(str(current_user["_id"]), payload)
