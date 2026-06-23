from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from app.models.engine_schemas import ExplanationPayload


class AlertSeveritySignals(BaseModel):
    fsi: float
    fsi_classification: str
    confirmed_disease: bool
    disease_name: Optional[str] = None
    possible_or_confirmed_disease: bool = False
    active_high_alerts: int = 0
    active_medium_alerts: int = 0
    active_low_alerts: int = 0
    active_alert_rules: List[str] = Field(default_factory=list)
    advisory_priority: str = "LOW"
    recent_sos: bool = False
    weather_temp_c: float = 0.0
    rainfall_deficit: float = 0.0
    rainfall_deficit_alert_active: bool = False


class AlertSeverityResult(BaseModel):
    farm_id: str
    severity_tier: str
    severity_rank: int
    critical_triggers: List[str] = Field(default_factory=list)
    generated_because: List[str] = Field(default_factory=list)
    explanation: ExplanationPayload
    signals: AlertSeveritySignals
    evaluated_at: datetime
    log_id: Optional[str] = None


class AlertSeverityResponse(BaseModel):
    severity: AlertSeverityResult
