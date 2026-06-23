from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.api.deps import get_current_user
from app.core.database import get_database
from app.models.farm_models import FarmProfileResponse
from app.services.onboarding_service import OnboardingService

router = APIRouter(prefix="/farms", tags=["farms"])


@router.get("/me", response_model=FarmProfileResponse)
async def get_my_farm(
    current_user: Annotated[dict, Depends(get_current_user)],
    request: Request,
) -> FarmProfileResponse:
    db = get_database()
    service = OnboardingService(db)
    accept_lang = request.headers.get("accept-language")
    language = accept_lang.split(",")[0].split(";")[0].strip().lower() if accept_lang else "en"
    if language not in ["hi", "en", "mr"]:
        language = "hi"
    return await service.get_farm_profile(str(current_user["_id"]), language=language)
