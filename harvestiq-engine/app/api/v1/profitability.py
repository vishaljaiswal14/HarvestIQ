from typing import Annotated, List
from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.api.deps import get_current_user
from app.core.database import get_database
from app.models.profitability_schemas import (
    ProfitabilityMetrics,
    CropCycleProfitability,
    FarmProfitabilitySummary,
    SeasonProfitability,
)
from app.services.profitability_service import ProfitabilityService

router = APIRouter(prefix="/profitability", tags=["profitability"])


@router.get("/crop-cycle/{crop_cycle_id}", response_model=CropCycleProfitability)
async def get_crop_cycle_profitability(
    crop_cycle_id: str,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncIOMotorDatabase, Depends(get_database)],
) -> CropCycleProfitability:
    service = ProfitabilityService(db)
    return await service.calculate_crop_cycle_metrics(str(current_user["_id"]), crop_cycle_id)


@router.get("/plot/{plot_id}", response_model=ProfitabilityMetrics)
async def get_plot_profitability(
    plot_id: str,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncIOMotorDatabase, Depends(get_database)],
) -> ProfitabilityMetrics:
    service = ProfitabilityService(db)
    return await service.calculate_plot_metrics(str(current_user["_id"]), plot_id)


@router.get("/farm/{farm_id}", response_model=FarmProfitabilitySummary)
async def get_farm_profitability(
    farm_id: str,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncIOMotorDatabase, Depends(get_database)],
) -> FarmProfitabilitySummary:
    service = ProfitabilityService(db)
    return await service.calculate_farm_summary(str(current_user["_id"]), farm_id)


@router.get("/farm/{farm_id}/season-comparison", response_model=List[SeasonProfitability])
async def get_farm_season_comparison(
    farm_id: str,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncIOMotorDatabase, Depends(get_database)],
) -> List[SeasonProfitability]:
    service = ProfitabilityService(db)
    return await service.calculate_season_comparison(str(current_user["_id"]), farm_id)
