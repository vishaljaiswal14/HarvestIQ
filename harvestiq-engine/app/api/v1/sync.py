from typing import Annotated

from fastapi import APIRouter, Depends, Request
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.api.deps import get_current_user
from app.core.database import get_database
from app.core.config import get_settings
from app.models.day7_schemas import SyncBatchRequest, SyncBatchResponse
from app.services.sync_service import SyncService

router = APIRouter(prefix="/sync", tags=["sync"])


@router.post("", response_model=SyncBatchResponse)
async def sync_outbox(
    request: Request,
    payload: SyncBatchRequest,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncIOMotorDatabase, Depends(get_database)],
) -> SyncBatchResponse:
    service = SyncService(db)
    settings = get_settings()
    if settings.external_callback_url:
        base_url = settings.external_callback_url.rstrip("/")
        status_callback = f"{base_url}/api/v1/sos/status-callback"
    else:
        status_callback = f"{request.base_url}api/v1/sos/status-callback"
    return await service.replay_batch(str(current_user["_id"]), payload, status_callback=status_callback)
