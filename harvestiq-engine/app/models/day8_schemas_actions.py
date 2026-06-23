from typing import List, Optional
from pydantic import BaseModel, Field

class ActionCard(BaseModel):
    card_type: str = Field(description="RED (Immediate), YELLOW (Monitor), GREEN (Healthy)")
    problem: str
    action: str
    deadline: str
    expected_impact: str
    is_sos: Optional[bool] = None

class AdvisoryActionsResponse(BaseModel):
    priority: str = Field(description="EMERGENCY, HIGH, MEDIUM, LOW")
    situation_summary: str
    today_actions: List[ActionCard]
    this_week_actions: List[ActionCard]
    ignore_risk: str
    why_generated: List[str]
