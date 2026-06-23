from datetime import date, datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, field_validator

from app.models.common import MongoModelConfig, PyObjectId


class CropStageDefinition(BaseModel):
    name: str
    gdd_min: float
    gdd_max: float


class CropCharacteristicsInDB(BaseModel):
    model_config = MongoModelConfig

    id: PyObjectId = Field(alias="_id")
    crop_type: str
    display_name: str
    gdd_base_temp: float
    stages: List[CropStageDefinition]
    stage_vulnerability: Dict[str, float] = Field(default_factory=dict)


class CropCycleCreateSchema(BaseModel):
    farm_id: str
    crop_type: str
    sowing_date: date

    @field_validator("sowing_date")
    @classmethod
    def validate_sowing_date(cls, value: date) -> date:
        if value > date.today():
            raise ValueError("Sowing date cannot be in the future")
        return value


class CropCycleCreateResponse(BaseModel):
    id: str
    status: str = "ACTIVE"


class DailyGddEntry(BaseModel):
    date: date
    gdd: float


class WeatherCurrent(BaseModel):
    temp: float
    humidity: float
    wind_speed: float
    precipitation: float


class WeatherForecastDay(BaseModel):
    date: date
    temp_min: float
    temp_max: float
    humidity: float
    precipitation: float
    wind_speed: float


class WeatherForecastResponse(BaseModel):
    farm_id: str
    current: WeatherCurrent
    forecast: List[WeatherForecastDay]
    daily_gdd: List[DailyGddEntry]
    source: str
    cached_at: datetime


class StageTimelineEntry(BaseModel):
    name: str
    gdd_min: float
    gdd_max: float
    is_current: bool = False
    is_completed: bool = False


class CropStageResponse(BaseModel):
    cycle_id: str
    crop_type: str
    stage: str
    progress_percentage: float
    current_gdd: float
    stages_timeline: List[StageTimelineEntry]


class ExplanationPayload(BaseModel):
    summary: str
    inputs: Dict[str, Any]
    primary_factor: str


class FsiComponents(BaseModel):
    temp_stress: float
    rainfall_deficit: float
    gdd_scale: float


class StressIndexResponse(BaseModel):
    farm_id: str
    crop_cycle_id: str
    crop_type: str
    stage: str
    fsi: float
    classification: str
    primary_factor: str
    components: FsiComponents
    calculated_at: datetime
    explanation: ExplanationPayload
    cycle_status: Optional[str] = None


class AlertResponse(BaseModel):
    id: str
    farm_id: str
    rule_id: str
    severity: str
    title: str
    message: str
    read: bool
    lifecycle_status: str = "CREATED"
    acknowledged_at: Optional[datetime] = None
    acknowledged_by: Optional[str] = None
    resolved_at: Optional[datetime] = None
    explanation: ExplanationPayload
    created_at: datetime


class AlertListResponse(BaseModel):
    alerts: List[AlertResponse]
    unread_count: int
    farm_severity: Optional[dict[str, Any]] = None


class TriggerEvaluationRequest(BaseModel):
    farm_id: str


class TriggerEvaluationResponse(BaseModel):
    farm_id: str
    evaluated_rules: int
    triggered_count: int
    alerts_created: List[AlertResponse]
    cycle_status: Optional[str] = None
    severity: Optional[dict[str, Any]] = None

