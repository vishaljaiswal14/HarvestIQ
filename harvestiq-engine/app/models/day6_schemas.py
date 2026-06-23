from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from app.models.engine_schemas import ExplanationPayload


class StressMomentumResult(BaseModel):
    direction: str
    momentum_score: float
    fsi_delta: float
    insufficient_history: bool = False
    window_days: int = 7


class YieldRiskResult(BaseModel):
    risk_band: str
    estimated_risk_percent: float
    contributing_factors: List[str] = Field(default_factory=list)


class InputWindowRequest(BaseModel):
    farm_id: str
    action_type: str


class InputWindowResponse(BaseModel):
    farm_id: str
    action_type: str
    safe: bool
    reasons: List[str]
    triggered_rules: List[str]
    explanation: ExplanationPayload
    evaluated_at: datetime
    cycle_status: Optional[str] = None



class SimulatorRequest(BaseModel):
    farm_id: str
    temp_delta: float = Field(default=0.0, ge=-10.0, le=10.0)
    irrigation_delta: float = Field(default=0.0, ge=-1.0, le=1.0)
    nitrogen_delta: float = Field(default=0.0, ge=-100.0, le=100.0)


class SimulatorSnapshot(BaseModel):
    fsi: float
    stress_momentum: StressMomentumResult
    yield_risk: YieldRiskResult
    fsi_curve: List[float] = Field(default_factory=list)
    yield_factor: float = 1.0


class SimulatorResponse(BaseModel):
    farm_id: str
    baseline: SimulatorSnapshot
    projected: SimulatorSnapshot
    explanation: ExplanationPayload
    intelligence_snapshot_version: str


class HealthCardResponse(BaseModel):
    farm_id: str
    crop_type: str
    stage: str
    fsi: float
    fsi_classification: str
    soil_health_index: Optional[float] = None
    stress_momentum: StressMomentumResult
    yield_risk: YieldRiskResult
    health_score: float
    health_band: str
    nearby_radar_high_count: int
    unread_alerts: int
    intelligence_snapshot_version: str
    explanation: ExplanationPayload
    cycle_status: Optional[str] = None



class BriefingSections(BaseModel):
    stress_momentum: StressMomentumResult
    yield_risk: YieldRiskResult
    input_windows: Dict[str, bool]
    market_summary: Optional[Dict[str, Any]] = None
    eligible_schemes_count: int = 0


class BriefingResponse(BaseModel):
    briefing_id: str
    farm_id: str
    synthesis: str
    language: str
    sections: BriefingSections
    explainability: ExplanationPayload
    intelligence_snapshot_version: str
    generated_at: datetime
    source: str


class SchemeMatch(BaseModel):
    scheme_id: str
    name: str
    description: str
    application_steps: List[str]


class SchemesEligibleResponse(BaseModel):
    farm_id: str
    schemes: List[SchemeMatch]
    evaluated_at: datetime


class MarketPriceRecord(BaseModel):
    mandi: str
    crop_type: str
    min_price: float
    max_price: float
    modal_price: float
    price_date: datetime


class MarketPricesResponse(BaseModel):
    farm_id: str
    crop_type: str
    prices: List[MarketPriceRecord]
    modal_trend: str
    as_of: datetime
    cycle_status: Optional[str] = None



class SimulatorHypothesis(BaseModel):
    temp_delta: float = 0.0
    irrigation_delta: float = 0.0
    nitrogen_delta: float = 0.0
    projected_fsi: Optional[float] = None


class CoreIntelligence(BaseModel):
    farm_id: str
    crop_type: str
    stage: str
    fsi: float
    fsi_classification: str
    primary_factor: str
    current_gdd: float
    soil_health_index: Optional[float] = None
    stress_momentum: StressMomentumResult
    yield_risk: YieldRiskResult
    mitigation_locked: bool
    disease_present: bool
    radar_high_nearby: bool
    nearby_outbreaks: List[str] = Field(default_factory=list)
    alert_rules: List[str] = Field(default_factory=list)
    stage_vulnerability: float = 0.5
    cycle_status: Optional[str] = None

