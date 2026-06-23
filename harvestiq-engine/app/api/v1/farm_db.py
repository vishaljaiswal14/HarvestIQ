from typing import Annotated, List

from fastapi import APIRouter, Depends, Response, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.api.deps import get_current_user
from app.core.database import get_database
from app.models.farm_models import (
    FarmerProfileSchema,
    FarmerProfileUpdate,
    FarmSchema,
    FarmCreateSchema,
    PlotSchema,
    PlotCreateSchema,
    CropCycleSchema,
    CropCycleCreateSchemaNew,
    ExpenseSchema,
    ExpenseCreateSchema,
    HarvestSchema,
    HarvestCreateSchema,
)
from app.services.farm_db_service import FarmDbService

router = APIRouter(prefix="/farm-db", tags=["farm-database"])


# --- Farmer Profile APIs ---
@router.get("/farmer/me", response_model=FarmerProfileSchema)
async def get_farmer_profile(
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncIOMotorDatabase, Depends(get_database)],
) -> FarmerProfileSchema:
    service = FarmDbService(db)
    return await service.get_farmer(str(current_user["_id"]))


@router.put("/farmer/me", response_model=FarmerProfileSchema)
async def update_farmer_profile(
    payload: FarmerProfileUpdate,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncIOMotorDatabase, Depends(get_database)],
) -> FarmerProfileSchema:
    service = FarmDbService(db)
    return await service.update_farmer(str(current_user["_id"]), payload)


# --- Farm CRUD APIs ---
@router.post("/farms", response_model=FarmSchema, status_code=201)
async def create_farm(
    payload: FarmCreateSchema,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncIOMotorDatabase, Depends(get_database)],
) -> FarmSchema:
    service = FarmDbService(db)
    return await service.create_farm(str(current_user["_id"]), payload)


@router.get("/farms", response_model=List[FarmSchema])
async def list_farms(
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncIOMotorDatabase, Depends(get_database)],
) -> List[FarmSchema]:
    service = FarmDbService(db)
    return await service.get_farms(str(current_user["_id"]))


@router.get("/farms/{farm_id}", response_model=FarmSchema)
async def get_farm(
    farm_id: str,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncIOMotorDatabase, Depends(get_database)],
) -> FarmSchema:
    service = FarmDbService(db)
    return await service.get_farm(str(current_user["_id"]), farm_id)


@router.put("/farms/{farm_id}", response_model=FarmSchema)
async def update_farm(
    farm_id: str,
    payload: FarmCreateSchema,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncIOMotorDatabase, Depends(get_database)],
) -> FarmSchema:
    service = FarmDbService(db)
    return await service.update_farm(str(current_user["_id"]), farm_id, payload)


@router.delete("/farms/{farm_id}", status_code=204)
async def delete_farm(
    farm_id: str,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncIOMotorDatabase, Depends(get_database)],
):
    service = FarmDbService(db)
    await service.delete_farm(str(current_user["_id"]), farm_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# --- Plot CRUD APIs ---
@router.post("/plots", response_model=PlotSchema, status_code=201)
async def create_plot(
    payload: PlotCreateSchema,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncIOMotorDatabase, Depends(get_database)],
) -> PlotSchema:
    service = FarmDbService(db)
    return await service.create_plot(str(current_user["_id"]), payload)


@router.get("/plots", response_model=List[PlotSchema])
async def list_plots(
    farm_id: str,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncIOMotorDatabase, Depends(get_database)],
) -> List[PlotSchema]:
    service = FarmDbService(db)
    return await service.get_plots(str(current_user["_id"]), farm_id)


@router.get("/plots/{plot_id}", response_model=PlotSchema)
async def get_plot(
    plot_id: str,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncIOMotorDatabase, Depends(get_database)],
) -> PlotSchema:
    service = FarmDbService(db)
    return await service.get_plot(str(current_user["_id"]), plot_id)


@router.put("/plots/{plot_id}", response_model=PlotSchema)
async def update_plot(
    plot_id: str,
    payload: PlotCreateSchema,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncIOMotorDatabase, Depends(get_database)],
) -> PlotSchema:
    service = FarmDbService(db)
    return await service.update_plot(str(current_user["_id"]), plot_id, payload)


@router.delete("/plots/{plot_id}", status_code=204)
async def delete_plot(
    plot_id: str,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncIOMotorDatabase, Depends(get_database)],
):
    service = FarmDbService(db)
    await service.delete_plot(str(current_user["_id"]), plot_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# --- Crop Cycle CRUD APIs ---
@router.post("/crop-cycles", response_model=CropCycleSchema, status_code=201)
async def create_crop_cycle_new(
    payload: CropCycleCreateSchemaNew,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncIOMotorDatabase, Depends(get_database)],
) -> CropCycleSchema:
    service = FarmDbService(db)
    return await service.create_crop_cycle(str(current_user["_id"]), payload)


@router.get("/crop-cycles", response_model=List[CropCycleSchema])
async def list_crop_cycles(
    plot_id: str,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncIOMotorDatabase, Depends(get_database)],
) -> List[CropCycleSchema]:
    service = FarmDbService(db)
    return await service.get_crop_cycles(str(current_user["_id"]), plot_id)


@router.get("/crop-cycles/active", response_model=List[CropCycleSchema])
async def list_active_crop_cycles(
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncIOMotorDatabase, Depends(get_database)],
) -> List[CropCycleSchema]:
    service = FarmDbService(db)
    return await service.get_active_crop_cycles(str(current_user["_id"]))


@router.get("/crop-cycles/{cycle_id}", response_model=CropCycleSchema)
async def get_crop_cycle_new(
    cycle_id: str,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncIOMotorDatabase, Depends(get_database)],
) -> CropCycleSchema:
    service = FarmDbService(db)
    return await service.get_crop_cycle(str(current_user["_id"]), cycle_id)


@router.put("/crop-cycles/{cycle_id}", response_model=CropCycleSchema)
async def update_crop_cycle_new(
    cycle_id: str,
    payload: CropCycleCreateSchemaNew,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncIOMotorDatabase, Depends(get_database)],
) -> CropCycleSchema:
    service = FarmDbService(db)
    return await service.update_crop_cycle(str(current_user["_id"]), cycle_id, payload)


@router.delete("/crop-cycles/{cycle_id}", status_code=204)
async def delete_crop_cycle_new(
    cycle_id: str,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncIOMotorDatabase, Depends(get_database)],
):
    service = FarmDbService(db)
    await service.delete_crop_cycle(str(current_user["_id"]), cycle_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# --- Expense CRUD APIs ---
@router.post("/expenses", response_model=ExpenseSchema, status_code=201)
async def create_expense(
    payload: ExpenseCreateSchema,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncIOMotorDatabase, Depends(get_database)],
) -> ExpenseSchema:
    service = FarmDbService(db)
    return await service.create_expense(str(current_user["_id"]), payload)


@router.get("/expenses", response_model=List[ExpenseSchema])
async def list_expenses(
    crop_cycle_id: str,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncIOMotorDatabase, Depends(get_database)],
) -> List[ExpenseSchema]:
    service = FarmDbService(db)
    return await service.get_expenses(str(current_user["_id"]), crop_cycle_id)


@router.get("/expenses/{expense_id}", response_model=ExpenseSchema)
async def get_expense(
    expense_id: str,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncIOMotorDatabase, Depends(get_database)],
) -> ExpenseSchema:
    service = FarmDbService(db)
    return await service.get_expense(str(current_user["_id"]), expense_id)


@router.put("/expenses/{expense_id}", response_model=ExpenseSchema)
async def update_expense(
    expense_id: str,
    payload: ExpenseCreateSchema,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncIOMotorDatabase, Depends(get_database)],
) -> ExpenseSchema:
    service = FarmDbService(db)
    return await service.update_expense(str(current_user["_id"]), expense_id, payload)


@router.delete("/expenses/{expense_id}", status_code=204)
async def delete_expense(
    expense_id: str,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncIOMotorDatabase, Depends(get_database)],
):
    service = FarmDbService(db)
    await service.delete_expense(str(current_user["_id"]), expense_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# --- Harvest CRUD APIs ---
@router.post("/harvests", response_model=HarvestSchema, status_code=201)
async def create_harvest(
    payload: HarvestCreateSchema,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncIOMotorDatabase, Depends(get_database)],
) -> HarvestSchema:
    service = FarmDbService(db)
    return await service.create_harvest(str(current_user["_id"]), payload)


@router.get("/harvests", response_model=List[HarvestSchema])
async def list_harvests(
    crop_cycle_id: str,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncIOMotorDatabase, Depends(get_database)],
) -> List[HarvestSchema]:
    service = FarmDbService(db)
    return await service.get_harvests(str(current_user["_id"]), crop_cycle_id)


@router.get("/harvests/{harvest_id}", response_model=HarvestSchema)
async def get_harvest(
    harvest_id: str,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncIOMotorDatabase, Depends(get_database)],
) -> HarvestSchema:
    service = FarmDbService(db)
    return await service.get_harvest(str(current_user["_id"]), harvest_id)


@router.put("/harvests/{harvest_id}", response_model=HarvestSchema)
async def update_harvest(
    harvest_id: str,
    payload: HarvestCreateSchema,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncIOMotorDatabase, Depends(get_database)],
) -> HarvestSchema:
    service = FarmDbService(db)
    return await service.update_harvest(str(current_user["_id"]), harvest_id, payload)


@router.delete("/harvests/{harvest_id}", status_code=204)
async def delete_harvest(
    harvest_id: str,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncIOMotorDatabase, Depends(get_database)],
):
    service = FarmDbService(db)
    await service.delete_harvest(str(current_user["_id"]), harvest_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
