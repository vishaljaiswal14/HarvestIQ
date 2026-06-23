from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field

from app.models.engine_schemas import ExplanationPayload


class YieldProtectionBreakdown(BaseModel):
    disease_risk: float = Field(ge=0, le=25)
    stress_risk: float = Field(ge=0, le=25)
    alert_burden: float = Field(ge=0, le=25)
    advisory_compliance: float = Field(ge=0, le=25)


class YieldProtectionScoreResponse(BaseModel):
    farm_id: str
    score: float = Field(ge=0, le=100)
    band: Literal["PROTECTED", "MODERATE", "AT_RISK", "CRITICAL"]
    breakdown: YieldProtectionBreakdown
    trend: Literal["IMPROVING", "STABLE", "DECLINING"]
    trend_delta: float
    top_risk: str
    risk_reduction_impact: str
    potential_loss_prevention_band: Literal["LOW", "MODERATE", "HIGH"]
    explanation: ExplanationPayload
    calculated_at: datetime
    log_id: Optional[str] = None


class YieldProtectionHistoryResponse(BaseModel):
    farm_id: str
    entries: list[dict]
    total: int
