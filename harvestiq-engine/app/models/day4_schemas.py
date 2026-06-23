from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator

from app.models.engine_schemas import ExplanationPayload


class KnowledgeChunkResult(BaseModel):
    text: str
    source: str
    score: float
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SoilRecordCreateSchema(BaseModel):
    farm_id: str
    nitrogen: float = Field(..., ge=0)
    phosphorus: float = Field(..., ge=0)
    potassium: float = Field(..., ge=0)
    ph: float = Field(..., ge=0, le=14)
    organic_carbon: float = Field(..., ge=0)
    electrical_conductivity: float = Field(..., ge=0)
    recorded_at: Optional[datetime] = None


class NutrientDeficiencyStatus(BaseModel):
    nitrogen: str
    phosphorus: str
    potassium: str
    ph: str
    organic_carbon: str
    electrical_conductivity: str


class SoilRecordUnavailableResponse(BaseModel):
    available: bool = False
    message: str = "No soil record submitted yet"


class SoilRecordResponse(BaseModel):
    id: str
    farm_id: str
    crop_type: str
    nitrogen: float
    phosphorus: float
    potassium: float
    ph: float
    organic_carbon: float
    electrical_conductivity: float
    deficiency_status: NutrientDeficiencyStatus
    soil_health_index: float
    explanation: ExplanationPayload
    recorded_at: datetime


class DiseaseDetectResponse(BaseModel):
    report_id: Optional[str] = None
    farm_id: str
    crop_type: str
    disease: str
    confidence: Optional[float] = None
    deterministic_status: str
    explanation: ExplanationPayload
    cycle_status: Optional[str] = None

    # Image Validation Metadata
    valid: bool = True
    image_type: Optional[str] = None
    validation_confidence: Optional[float] = None
    reason: Optional[str] = None
    message: Optional[str] = None

    # Actionable guidance upgrade
    disease_name: Optional[str] = None
    severity: Optional[str] = None
    what_it_means: Optional[str] = None
    immediate_actions: Optional[List[str]] = None
    recommended_treatment: Optional[str] = None
    prevention_advice: Optional[List[str]] = None
    risk_level: Optional[str] = None

    # Explainability & Serving fields
    crop_confidence: Optional[float] = None
    validation_result: Optional[bool] = None
    region_validation_result: Optional[bool] = None
    created_at: Optional[datetime] = None
    image_url: Optional[str] = None
    image_path: Optional[str] = None


class KnowledgeDocumentMeta(BaseModel):
    document_id: str
    title: str
    source: str
    crop_type: str
    state: str
    district: str = "ALL"
    season: str = "ALL"
    topic: str
    language: str = "en"

    @field_validator("crop_type", "state", "district", "season", "topic", mode="before")
    @classmethod
    def normalize_upper(cls, value: str) -> str:
        if isinstance(value, str):
            return value.strip().upper().replace(" ", "_")
        return value


class KnowledgeMetadataInDB(BaseModel):
    document_id: str
    title: str
    source: str
    crop_type: str
    state: str
    district: str
    season: str
    topic: str
    language: str = "en"
    chunk_count: int
    indexed_at: datetime


class HybridSearchParams(BaseModel):
    query: str
    crop_type: Optional[str] = None
    state: Optional[str] = None
    district: Optional[str] = None
    season: Optional[str] = None
    topic: Optional[str] = None
    limit: int = Field(default=5, ge=1, le=20)
