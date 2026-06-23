from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class CopilotAction(BaseModel):
    id: str
    horizon: Literal["TODAY", "THIS_WEEK", "PREVENTIVE"]
    priority: Literal["EMERGENCY", "HIGH", "MEDIUM", "LOW"]
    card_type: Literal["RED", "YELLOW", "GREEN"]
    title: str
    action: str
    deadline: str
    expected_impact: str
    why: str
    if_ignored: str
    expected_benefit: str
    source_signals: List[str] = Field(default_factory=list)
    is_sos: bool = False
    completed: bool = False


class OperationsCopilotResponse(BaseModel):
    farm_id: str
    crop_type: str
    stage: str
    priority: str
    severity_tier: str
    situation_summary: str
    today_actions: List[CopilotAction]
    this_week_actions: List[CopilotAction]
    preventive_actions: List[CopilotAction]
    risk_reduction_impact: str
    potential_loss_prevention_band: Literal["LOW", "MODERATE", "HIGH"]
    why_generated: List[str]
    generated_at: datetime
    plan_id: str
    yield_protection_score: Optional[float] = None
    yield_protection_band: Optional[str] = None


class CopilotActionCompleteRequest(BaseModel):
    plan_id: str


class CopilotActionCompleteResponse(BaseModel):
    action_id: str
    completed: bool
    yield_protection_score: Optional[float] = None
