from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import get_current_user, require_roles
from app.core.database import get_database
from app.models.farm_models import OnboardingResponse, OnboardingSchema
from app.services.onboarding_service import OnboardingService

router = APIRouter(tags=["onboarding"])


@router.post("/onboarding", response_model=OnboardingResponse, status_code=201)
async def complete_onboarding(
    payload: OnboardingSchema,
    current_user: Annotated[dict, Depends(require_roles("FARMER", "AGRONOMIST", "ADMIN"))],
) -> OnboardingResponse:
    db = get_database()
    service = OnboardingService(db)
    return await service.complete_onboarding(str(current_user["_id"]), payload)
