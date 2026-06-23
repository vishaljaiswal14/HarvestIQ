from typing import Annotated

from fastapi import APIRouter, Depends, Query
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.api.deps import get_current_user
from app.core.database import get_database
from app.models.day6_schemas import SchemesEligibleResponse
from app.services.scheme_eligibility_service import SchemeEligibilityService

router = APIRouter(prefix="/schemes", tags=["schemes"])


@router.get("/eligible", response_model=SchemesEligibleResponse)
async def get_eligible_schemes(
    farm_id: Annotated[str, Query()],
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncIOMotorDatabase, Depends(get_database)],
) -> SchemesEligibleResponse:
    service = SchemeEligibilityService(db)
    return await service.get_eligible(str(current_user["_id"]), farm_id)
