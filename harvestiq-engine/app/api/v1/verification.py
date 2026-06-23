from typing import Annotated

from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.api.deps import get_current_user
from app.core.database import get_database
from app.models.day7_schemas import VerificationLogRequest, VerificationLogResponse
from app.services.verification_log_service import VerificationLogService

router = APIRouter(prefix="/verification", tags=["verification"])


@router.post("/log", response_model=VerificationLogResponse)
async def record_verification(
    payload: VerificationLogRequest,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncIOMotorDatabase, Depends(get_database)],
) -> VerificationLogResponse:
    service = VerificationLogService(db)
    return await service.record(
        event_type=payload.event_type,
        environment=payload.environment,
        status=payload.status,
        details=payload.details,
    )
