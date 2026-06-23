from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.core.database import get_database
from app.models.engine_schemas import StressIndexResponse
from app.services.stress_index_service import StressIndexService

router = APIRouter(prefix="/stress-index", tags=["stress-index"])


@router.get("/{farm_id}", response_model=StressIndexResponse)
async def get_stress_index(
    farm_id: str,
    current_user: Annotated[dict, Depends(get_current_user)],
) -> StressIndexResponse:
    db = get_database()
    service = StressIndexService(db)
    lang = current_user.get("preferred_lang", "hi")
    return await service.compute(farm_id, str(current_user["_id"]), language=lang)
