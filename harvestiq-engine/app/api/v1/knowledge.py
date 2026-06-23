from typing import Annotated

from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.api.deps import get_current_user
from app.core.database import get_database
from app.models.knowledge_schemas import KnowledgeSyncResponse
from app.services.knowledge_sync_service import KnowledgeSyncService

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


@router.get("/sync", response_model=KnowledgeSyncResponse)
async def sync_knowledge(
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncIOMotorDatabase, Depends(get_database)],
) -> KnowledgeSyncResponse:
    service = KnowledgeSyncService(db)
    return await service.get_sync_payload()
