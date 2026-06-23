from datetime import date, datetime
from typing import List, Literal, Optional, Tuple

from pydantic import BaseModel, Field, field_validator

from app.models.common import MongoModelConfig, PyObjectId

SoilType = Literal["CLAY", "SANDY", "LOAM", "SILT"]
AreaUnit = Literal["ACRE", "HECTARE", "SQM"]
CropCycleStatus = Literal["ACTIVE", "HARVESTED", "FAILED"]
ExpenseCategory = Literal[
    "SEEDS",
    "FERTILIZER",
    "PESTICIDES",
    "IRRIGATION_FUEL",
    "LABOR",
    "MACHINERY_RENT",
    "TRANSPORT",
    "LAND_RENT",
    "OTHER",
]


class GeoJSONPolygon(BaseModel):
    type: Literal["Polygon"] = "Polygon"
    coordinates: List[List[Tuple[float, float]]]

    @field_validator("coordinates")
    @classmethod
    def validate_coordinates(cls, value: List[List[Tuple[float, float]]]) -> List[List[Tuple[float, float]]]:
        if not value:
            raise ValueError("Polygon coordinates cannot be empty")
        for ring in value:
            if len(ring) < 4:
                raise ValueError("Polygon ring must have at least 4 coordinate pairs")
            for lon, lat in ring:
                if not (-180 <= lon <= 180):
                    raise ValueError("Longitude must be between -180 and 180")
                if not (-90 <= lat <= 90):
                    raise ValueError("Latitude must be between -90 and 90")
            if ring[0] != ring[-1]:
                raise ValueError("Polygon ring must be closed (first and last points must match)")
        return value


class OnboardingSchema(BaseModel):
    crop_type: str = Field(..., min_length=1, max_length=50)
    state: str = Field(..., min_length=1, max_length=50)
    district: str = Field(..., min_length=1, max_length=50)
    sowing_date: date
    farm_name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    soil_type: Optional[SoilType] = None
    boundary: Optional[GeoJSONPolygon] = None

    @field_validator("sowing_date")
    @classmethod
    def validate_sowing_date(cls, value: date) -> date:
        if value > date.today():
            raise ValueError("Sowing date cannot be in the future")
        return value


class FarmInDB(BaseModel):
    model_config = MongoModelConfig

    id: PyObjectId = Field(alias="_id")
    user_id: PyObjectId
    name: str
    state: str
    district: str
    boundary: Optional[dict] = None
    soil_type: Optional[str] = None
    created_at: datetime


class CropCycleInDB(BaseModel):
    model_config = MongoModelConfig

    id: PyObjectId = Field(alias="_id")
    farm_id: PyObjectId
    crop_type: str
    sowing_date: datetime
    current_gdd: float = 0.0
    status: Literal["ACTIVE", "HARVESTED"] = "ACTIVE"
    updated_at: datetime


class OnboardingResponse(BaseModel):
    status: str = "onboarded"
    farm_id: str
    crop_cycle_id: str
    onboarding_completed: bool = True


class FarmProfileResponse(BaseModel):
    farm_id: str
    farm_name: str
    state: str
    district: str
    soil_type: Optional[str] = None
    boundary: Optional[dict] = None
    crop_cycle_id: Optional[str] = None
    crop_type: Optional[str] = None
    sowing_date: Optional[date] = None


class FarmerProfileSchema(BaseModel):
    id: str
    name: str
    preferred_language: str
    state: str
    district: str
    created_at: datetime


class FarmerProfileUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=50)
    preferred_language: Optional[str] = Field(None, min_length=2, max_length=5)
    state: Optional[str] = Field(None, min_length=2, max_length=50)
    district: Optional[str] = Field(None, min_length=2, max_length=50)


class FarmCreateSchema(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    area: float = Field(..., ge=0.0)
    area_unit: AreaUnit = "ACRE"
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)


class FarmSchema(BaseModel):
    id: str
    farmer_id: str
    name: str
    area: float
    area_unit: AreaUnit
    latitude: float
    longitude: float
    created_at: datetime


class PlotCreateSchema(BaseModel):
    farm_id: str
    name: str = Field(..., min_length=1, max_length=100)
    area: float = Field(..., ge=0.0)
    area_unit: AreaUnit = "ACRE"


class PlotSchema(BaseModel):
    id: str
    farm_id: str
    name: str
    area: float
    area_unit: AreaUnit


class CropCycleCreateSchemaNew(BaseModel):
    plot_id: str
    crop_type: str = Field(..., min_length=1, max_length=50)
    season: str = Field(..., min_length=1, max_length=50)
    sowing_date: date
    expected_harvest_date: date


class CropCycleSchema(BaseModel):
    id: str
    plot_id: str
    crop_type: str
    season: str
    sowing_date: date
    expected_harvest_date: date
    status: CropCycleStatus


class ExpenseCreateSchema(BaseModel):
    crop_cycle_id: str
    category: ExpenseCategory
    amount: float = Field(..., ge=0.0)
    notes: Optional[str] = Field(None, max_length=500)
    expense_date: date


class ExpenseSchema(BaseModel):
    id: str
    crop_cycle_id: str
    category: ExpenseCategory
    amount: float
    notes: Optional[str]
    expense_date: date


class HarvestCreateSchema(BaseModel):
    crop_cycle_id: str
    yield_quantity: float = Field(..., ge=0.0)
    yield_unit: str = Field(..., min_length=1, max_length=20)
    revenue: float = Field(..., ge=0.0)
    harvest_date: date


class HarvestSchema(BaseModel):
    id: str
    crop_cycle_id: str
    yield_quantity: float
    yield_unit: str
    revenue: float
    harvest_date: date
