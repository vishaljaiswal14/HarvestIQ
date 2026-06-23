from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from app.models.engine_schemas import ExplanationPayload


class AdvisoryAskRequest(BaseModel):
    farm_id: str
    query: str = Field(..., min_length=1, max_length=2000)
    language: Optional[str] = Field(default=None, min_length=2, max_length=5)


class AdvisoryCitation(BaseModel):
    source: str
    document_id: str
    title: str = ""
    excerpt: str = ""


class AdvisoryAskResponse(BaseModel):
    advisory_id: str
    farm_id: str
    synthesis: str
    advisory_text: Optional[str] = None
    language: str
    explainability: ExplanationPayload
    explanation: Optional[Dict[str, Any]] = None
    citations: List[AdvisoryCitation]
    intelligence_snapshot_version: str


class DiseaseRadarHotspot(BaseModel):
    disease_name: str
    crop_type: str
    risk_level: str
    case_count: int
    distance_km: float
    location_grid: Dict[str, Any]
    last_updated: datetime


class DiseaseRadarNearbyResponse(BaseModel):
    hotspots: List[DiseaseRadarHotspot]
    queried_at: datetime
    radius_km: float


class VoiceTranscribeResponse(BaseModel):
    transcript: str
    confidence: float
    language: str


class LocalizationResponse(BaseModel):
    lang: str
    labels: Dict[str, str]


class CompiledContextResult(BaseModel):
    context_package: str
    context_hash: str
    citations: List[AdvisoryCitation]
    explainability: Dict[str, Any]
    rag_chunk_ids: List[str]
    intelligence_snapshot_version: str
    mitigation_locked: bool
    language: str
