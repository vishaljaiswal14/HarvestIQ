from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from app.models.day4_schemas import DiseaseDetectResponse

class DiseaseHistoryListResponse(BaseModel):
    reports: List[DiseaseDetectResponse]
    total: int
    page: int
    limit: int

class TimelineEvent(BaseModel):
    id: str
    type: str
    timestamp: datetime
    title: str
    description: str
    action: Optional[str] = None
    severity: Optional[str] = None
    risk_level: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

class FarmTimelineResponse(BaseModel):
    farm_id: str
    events: List[TimelineEvent]

class DemoSeedResponse(BaseModel):
    success: bool
    message: str
    farms: List[Dict[str, Any]]
